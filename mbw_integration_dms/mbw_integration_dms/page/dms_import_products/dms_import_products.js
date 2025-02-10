frappe.pages['dms-import-products'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'DMS Import Products',
		single_column: true
	});
	new ProductImporter(wrapper)
}

ProductImporter = class {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");
		this.page = wrapper.page;
		this.init();
		this.syncRunning = false;
	}

	init() {
		frappe.run_serially([
			() => this.addMarkup(),
			() => this.fetchProductCount(),
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
				(job) => job.job_name == "dms.job.sync.all.products"
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
                        <h5 class="border-bottom pb-2">Products in DMS</h5>
                        <div id="dms-product-list">
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
                                    <button type="button" id="btn-sync-all" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Sync all Products</button>
                                </div>
                                <div class="product-count py-3 d-flex justify-content-stretch">
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-products-erpnext">-</h2>
                                        <p class="text-muted m-0">in ERPNext</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-products-pending">-</h2>
                                        <p class="text-muted m-0">Pending sync</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-products-synced">-</h2>
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

	async fetchProductCount() {
		try {
			const {
				message: { erpnextCount, pendingCount, syncedCount },
			} = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_products.get_count_products",
			});

			this.wrapper.find("#count-products-pending").text(pendingCount);
			this.wrapper.find("#count-products-erpnext").text(erpnextCount);
			this.wrapper.find("#count-products-synced").text(syncedCount);
		} catch (error) {
			frappe.throw(__("Error fetching product count."));
		}
	}

	async addTable() {
		const listElement = this.wrapper.find("#dms-product-list")[0];
		this.dmsProductTable = new frappe.DataTable(listElement, {
			columns: [
				{
					name: "Item Code",
					align: "left",
					editable: false,
					focusable: false,
					width: 200,
				},
				{
					name: "Item Name",
					align: "left",
					editable: false,
					focusable: false,
					width: 250,
				},
				{
					name: "Status",
					align: "center",
					editable: false,
					focusable: false,
					width: 150,
				},
				{
					name: "Action",
					align: "center",
					editable: false,
					focusable: false,
					width: 150,
				},
			],
			data: await this.fetchdmsProducts(),
			layout: "fixed",
		});

		this.wrapper.find(".dms-datatable-footer").show();
	}

	async fetchdmsProducts(page = 1) {
		try {
			const {
				message: products,
			} = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_products.get_products",
				args: { page },
			});
			this.next_page = page + 1;
			this.prev_page = page > 1 ? page - 1 : page;

			const dmsProducts = products.map((product) => ({
				// 'Image': product.image && product.image.src && `<img style="height: 50px" src="${product.image.src}">`,
				"Item Code": product.item_code,
				"Item Name": product.item_name,
				Status: this.getProductSyncStatus(product.is_sync),
				Action: !product.is_sync
					? `<button type="button" class="btn btn-default btn-xs btn-sync mx-2" data-product="${product.id}"> Sync </button>`
					: `<button type="button" class="btn btn-default btn-xs btn-resync mx-2" data-product="${product.id}"> Re-sync </button>`,
			}));

			return dmsProducts;
		} catch (error) {
			frappe.throw(__("Error fetching products."));
		}
	}

	getProductSyncStatus(status) {
		return status
			? `<span class="indicator-pill green">Synced</span>`
			: `<span class="indicator-pill orange">Not Synced</span>`;
	}

	listen() {
		// sync a product from table
		this.wrapper.on("click", ".btn-sync", (e) => {
			const _this = $(e.currentTarget);

			_this.prop("disabled", true).text("Syncing...");

			const product = _this.attr("data-product");
			this.syncProduct(product).then((status) => {
				if (!status) {
					frappe.throw(__("Error syncing product"));
					_this.prop("disabled", false).text("Sync");
					return;
				}

				_this
					.parents(".dt-row")
					.find(".indicator-pill")
					.replaceWith(this.getProductSyncStatus(true));

				_this.replaceWith(
					`<button type="button" class="btn btn-default btn-xs btn-resync mx-2" data-product="${product}"> Re-sync </button>`
				);
			});
		});

		this.wrapper.on("click", ".btn-resync", (e) => {
			const _this = $(e.currentTarget);

			_this.prop("disabled", true).text("Syncing...");

			const product = _this.attr("data-product");
			this.resyncProduct(product)
				.then((status) => {
					if (!status) {
						frappe.throw(__("Error syncing product"));
						return;
					}

					_this
						.parents(".dt-row")
						.find(".indicator-pill")
						.replaceWith(this.getProductSyncStatus(true));

					_this.prop("disabled", false).text("Re-sync");
				})
				.catch((ex) => {
					_this.prop("disabled", false).text("Re-sync");
					frappe.throw(__("Error syncing Product"));
				});
		});

		// pagination
		this.wrapper.on("click", ".btn-prev,.btn-next", (e) =>
			this.switchPage(e)
		);

		// sync all products
		this.wrapper.on("click", "#btn-sync-all", (e) => this.syncAll(e));
	}

	async syncProduct(product) {
		const { message: status } = await frappe.call({
			method: "dms_import_products.dms_import_products.sync_product",
			args: { product },
		});

		if (status) this.fetchProductCount();

		return status;
	}

	async resyncProduct(product) {
		const { message: status } = await frappe.call({
			method: "dms_import_products.dms_import_products.resync_product",
			args: { product },
		});

		if (status) this.fetchProductCount();

		return status;
	}

	async switchPage({ currentTarget }) {
		const _this = $(currentTarget);

		$(".btn-paginate").prop("disabled", true);
		this.dmsProductTable.showToastMessage("Loading...");

		const newProducts = await this.fetchdmsProducts(
			_this.hasClass("btn-next") ? this.next_page : this.prev_page
		);

		this.dmsProductTable.refresh(newProducts);

		$(".btn-paginate").prop("disabled", false);
		this.dmsProductTable.clearToastMessage();
	}

	syncAll() {
		this.checkSyncStatus();
		this.toggleSyncAllButton();

		if (this.syncRunning) {
			frappe.msgprint(__("Sync already in progress"));
		} else {
			frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_products.sync_all_products",
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
		const _syncedCounter = $("#count-products-synced");
		const _erpnextCounter = $("#count-products-erpnext");

		frappe.realtime.on(
			"dms.key.sync.all.products",
			({ message, synced, done, error }) => {
				message = `<pre class="mb-0">${message}</pre>`;
				_log.append(message);
				_log.scrollTop(_log[0].scrollHeight);

				if (synced)
					this.updateSyncedCount(_syncedCounter, _erpnextCounter);

				if (done) {
					frappe.realtime.off("dms.key.sync.all.products");
					this.toggleSyncAllButton(false);
					this.fetchProductCount();
					this.syncRunning = false;
				}
			}
		);
	}

	toggleSyncAllButton(disable = true) {
		const btn = $("#btn-sync-all");

		const _toggleClass = (d) => (d ? "btn-success" : "btn-primary");
		const _toggleText = () => (disable ? "Syncing..." : "Sync Products");

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
};
