frappe.pages['dms-import-category'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'DMS Import Category',
		single_column: true
	});
	new CategoryImporter(wrapper);
}

CategoryImporter = class {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");
		this.init();
		this.syncRunning = false;
	}

	init() {
		frappe.run_serially([
			() => this.addMarkup(),
			// () => this.fetchCategoryCount(),
			() => this.addTable(),
			() => this.checkSyncStatus(),
			() => this.listen(),
		]);
	}

	async checkSyncStatus() {
		const jobs = await frappe.db.get_list("RQ Job", {
			filters: { status: ("in", ("queued", "started")) },
		});
		this.syncRunning =
			jobs.find(
				(job) => job.job_name == "dms.job.sync.all.categories"
			) !== undefined;

		if (this.syncRunning) {
			this.toggleSyncAllButton();
			this.logSync();
		}
	}

	addMarkup() {
		const _markup = $(`
            <div class="row">
                <div class="col-lg-8 d-flex align-items-stretch">
                    <div class="card border-0 shadow-sm p-3 mb-3 w-100 rounded-sm" style="background-color: var(--card-bg)">
                        <h5 class="border-bottom pb-2">Category in DMS</h5>
                        <div id="dms-category-list">
                            <div class="text-center">Loading...</div>
                        </div>
                        <div class="dms-datatable-footer mt-2 pt-3 pb-2 border-top text-right" style="display: none">
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-prev">Prev</button>
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-next">Next</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4 d-flex align-items-stretch">
                    <div class="w-100">
                        <div class="card border-0 shadow-sm p-3 mb-3 rounded-sm" style="background-color: var(--card-bg)">
                            <h5 class="border-bottom pb-2">Synchronization Details</h5>
                            <div id="dms-sync-info">
                                <div class="py-3 border-bottom">
                                    <button type="button" id="btn-sync-all" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Sync all categories</button>
                                </div>
                                <div class="category-count py-3 d-flex justify-content-stretch">
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-categories-dms">-</h2>
                                        <p class="text-muted m-0">in DMS</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-categories-erpnext">-</h2>
                                        <p class="text-muted m-0">in ERPNext</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-categories-synced">-</h2>
                                        <p class="text-muted m-0">Synced</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="card border-0 shadow-sm p-3 mb-3 rounded-sm" style="background-color: var(--card-bg); display: none;">
                            <h5 class="border-bottom pb-2">Sync Log</h5>
                            <div class="control-value like-disabled-input for-description overflow-auto" id="dms-sync-log" style="max-height: 500px;"></div>
                        </div>

                    </div>
                </div>
            </div>
        `);

		this.wrapper.append(_markup);
	}

	async fetchCategoryCount() {
		try {
			const {
				message: { erpnextCount, dmsCount, syncedCount },
			} = await frappe.call({
				method: "dms_import_categories.dms_import_categories.get_category_count",
			});

			this.wrapper.find("#count-categories-dms").text(dmsCount);
			this.wrapper.find("#count-categories-erpnext").text(erpnextCount);
			this.wrapper.find("#count-categories-synced").text(syncedCount);
		} catch (error) {
			frappe.throw(__("Error fetching category count."));
		}
	}

	async addTable() {
		const listElement = this.wrapper.find("#dms-category-list")[0];
		this.dmsCategoryTable = new frappe.DataTable(listElement, {
			columns: [
				// {
				//     name: 'Image',
				//     align: 'center',
				// },
				{
					name: "Name",
					editable: false,
					focusable: false,
				},
				{
					name: "Category",
					editable: false,
					focusable: false,
				},
				{
					name: "Doctype",
					align: "center",
					editable: false,
					focusable: false,
				},
				{
					name: "Status",
					align: "center",
					editable: false,
					focusable: false,
				},
			],
			data: await this.fetchdmsCategories(),
			layout: "fixed",
		});

		this.wrapper.find(".dms-datatable-footer").show();
	}

	async fetchdmsCategories(page=1) {
		try {
			const {
				message: categories }
			  = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_category.dms_import_category.get_categories",
				args: { page: page},
			});
			this.next_page = page + 1;
			this.prev_page = page > 1 ? page - 1 : page;
			const dmsCategories = categories.map((category) => ({
				// 'Image': category.image && category.image.src && `<img style="height: 50px" src="${category.image.src}">`,
				Name: category.name,
				Category: category.category,
				Doctype: category.doctype,
				Status: !category.is_sync
					? `<button type="button" class="btn btn-default btn-xs btn-sync mx-2" data-category="${category.name}"> Sync </button>`
					: `<button type="button" class="btn btn-default btn-xs btn-resync mx-2" data-category="${category.name}"> Synced </button>`,
			}));

			return dmsCategories;
		} catch (error) {
			console.log(error)
			frappe.throw(__("Error fetching categories."));
		}
	}

	getCategoriesyncStatus(status) {
		return status
			? `<span class="indicator-pill green">Synced</span>`
			: `<span class="indicator-pill orange">Not Synced</span>`;
	}

	listen() {
		// sync a category from table
		this.wrapper.on("click", ".btn-sync", (e) => {
			const _this = $(e.currentTarget);

			_this.prop("disabled", true).text("Syncing...");

			const category = _this.attr("data-category");
			this.syncCategory(category).then((status) => {
				if (!status) {
					frappe.throw(__("Error syncing category"));
					_this.prop("disabled", false).text("Sync");
					return;
				}

				_this
					.parents(".dt-row")
					.find(".indicator-pill")
					.replaceWith(this.getCategoriesyncStatus(true));

				_this.replaceWith(
					`<button type="button" class="btn btn-default btn-xs btn-resync mx-2" data-category="${category}"> Re-sync </button>`
				);
			});
		});

		this.wrapper.on("click", ".btn-resync", (e) => {
			const _this = $(e.currentTarget);

			_this.prop("disabled", true).text("Syncing...");

			const category = _this.attr("data-category");
			this.resynccategory(category)
				.then((status) => {
					if (!status) {
						frappe.throw(__("Error syncing category"));
						return;
					}

					_this
						.parents(".dt-row")
						.find(".indicator-pill")
						.replaceWith(this.getCategoriesyncStatus(true));

					_this.prop("disabled", false).text("Re-sync");
				})
				.catch((ex) => {
					_this.prop("disabled", false).text("Re-sync");
					frappe.throw(__("Error syncing category"));
				});
		});

		// pagination
		this.wrapper.on("click", ".btn-prev,.btn-next", (e) =>
			this.switchPage(e)
		);

		// sync all categories
		this.wrapper.on("click", "#btn-sync-all", (e) => this.syncAll(e));
	}

	async syncCategory(category) {
		const { message: status } = await frappe.call({
			method: "dms_import_categories.dms_import_categories.sync_category",
			args: { category },
		});

		if (status) this.fetchCategoryCount();

		return status;
	}

	async resyncCategory(category) {
		const { message: status } = await frappe.call({
			method: "dms_import_categories.dms_import_categories.resync_category",
			args: { category },
		});

		if (status) this.fetchCategoryCount();

		return status;
	}

	async switchPage({ currentTarget }) {
		const _this = $(currentTarget);

		$(".btn-paginate").prop("disabled", true);
		this.dmsCategoryTable.showToastMessage("Loading...");

		const newCategories = await this.fetchdmsCategories(
			_this.hasClass("btn-next") ? this.next_page : this.prev_page
		);

		this.dmsCategoryTable.refresh(newCategories);

		$(".btn-paginate").prop("disabled", false);
		this.dmsCategoryTable.clearToastMessage();
	}

	syncAll() {
		this.checkSyncStatus();
		this.toggleSyncAllButton();

		if (this.syncRunning) {
			frappe.msgprint(__("Sync already in progress"));
		} else {
			frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_category.dms_import_category.sync_all_categories",
			});
		}

		// sync progress
		// this.logSync();
	}

	logSync() {
		const _log = $("#dms-sync-log");
		_log.parents(".card").show();
		_log.text(""); // clear logs

		// define counters here to prevent calling jquery every time
		const _syncedCounter = $("#count-categories-synced");
		const _erpnextCounter = $("#count-categories-erpnext");

		frappe.realtime.on(
			"dms.key.sync.all.categories",
			({ message, synced, done, error }) => {
				message = `<pre class="mb-0">${message}</pre>`;
				_log.append(message);
				_log.scrollTop(_log[0].scrollHeight);

				if (synced)
					this.updateSyncedCount(_syncedCounter, _erpnextCounter);

				if (done) {
					frappe.realtime.off("dms.key.sync.all.categories");
					this.toggleSyncAllButton(false);
					this.fetchCategoryCount();
					this.syncRunning = false;
				}
			}
		);
	}

	toggleSyncAllButton(disable = true) {
		const btn = $("#btn-sync-all");

		const _toggleClass = (d) => (d ? "btn-success" : "btn-primary");
		const _toggleText = () => (disable ? "Syncing..." : "Sync categories");

		btn.prop("disabled", disable)
			.addClass(_toggleClass(disable))
			.removeClass(_toggleClass(!disable))
			.text(_toggleText());
	}

	updateSyncedCount(_syncedCounter, _erpnextCounter) {
		let _synced = parseFloat(_syncedCounter.text());
		let _erpnext = parseFloat(_erpnextCounter.text());

		_syncedCounter.text(_synced + 1);
		_erpnextCounter.text(_erpnext + 1);
	}
}