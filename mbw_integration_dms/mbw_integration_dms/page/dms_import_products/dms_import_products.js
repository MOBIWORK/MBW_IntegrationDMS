frappe.pages['dms-import-products'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Sync ERPNext and DMS',
		single_column: true
	});
	new ProductImporter(wrapper)
	new CustomerImporter(wrapper)
	// new SalesOrderImporter(wrapper)
	new CategoryImporter(wrapper)
	new KPIImporter(wrapper)

}

KPIImporter = class {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");
		this.page = wrapper.page;
		this.init();
		this.syncRunning = false;
	}
	init() {
		frappe.run_serially([
			() => this.addMarkup(),
			() => this.listen()])
	}
	addMarkup() {
		const _markup = $(`<div class="card border-0 shadow-sm p-3 mb-3 rounded-sm" style="background-color: var(--card-bg)">
            <h5 class="border-bottom pb-2">Lấy dữ liệu DMS thủ công</h5>
			<div class="row">
				<div class="col-lg-6 d-flex align-items-stretch">
					<div class="w-100">
						<div class="py-3 border-bottom">
							<button type="button" id="btn-get-dms-kpi" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Lấy dữ liệu KPI</button>
						</div>
						<div class="card border-0 shadow-sm p-3 mb-3 rounded-sm" style="background-color: var(--card-bg); display: none;">
                            <h5 class="border-bottom pb-2">Sync Log</h5>
                            <div class="control-value like-disabled-input for-description overflow-auto" id="kpi-sync-log" style="max-height: 500px;"></div>
                    	</div>
					</div>
				</div>
				<div class="col-lg-6 d-flex align-items-stretch">
					<div class="w-100">
						<div class="py-3 border-bottom">
							<button type="button" id="btn-get-dms-timesheet" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Lấy dữ liệu bảng công</button>
						</div>
						<div class="card border-0 shadow-sm p-3 mb-3 rounded-sm" style="background-color: var(--card-bg); display: none;">
                            <h5 class="border-bottom pb-2">Sync Log</h5>
                            <div class="control-value like-disabled-input for-description overflow-auto" id="timesheet-sync-log" style="max-height: 500px;"></div>
                     	</div>
					</div>
			</div>`)
		this.wrapper.append(_markup);
	}

	listen() {
		this.wrapper.on("click", "#btn-get-dms-kpi", (e) => this.getKPI(e));
		this.wrapper.on("click", "#btn-get-dms-timesheet", (e) => this.getTimesheet(e));
	}
	getKPI() {
		this.togglegetKPI()
		frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_products.get_dms_kpi",
			});
		this.logSynckpi()
	}
	getTimesheet() {
		this.togglegetTimesheet()
		frappe.call({
			method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_products.get_dms_timesheet",
		});

		this.logSyncTimesheet();
	}

	logSynckpi() {
		const _log = $("#kpi-sync-log");
		_log.parents(".card").show();
		_log.text(""); // clear logs
		frappe.realtime.on(
			"dms.key.sync.all.kpi",
			({ message, synced, done, error }) => {
				message = `<pre class="mb-0">${message}</pre>`;
				_log.append(message);
				_log.scrollTop(_log[0].scrollHeight);
				if (done) {
					frappe.realtime.off("dms.key.sync.all.kpi");
					this.togglegetKPI(false);
					this.syncRunning = false;
				}
			}
		);
	}
	logSyncTimesheet() {
		const _log = $("#timesheet-sync-log");
		_log.parents(".card").show();
		_log.text(""); // clear logs
		frappe.realtime.on(
			"dms.key.sync.all.timesheet",
			({ message, synced, done, error }) => {
				message = `<pre class="mb-0">${message}</pre>`;
				_log.append(message);
				_log.scrollTop(_log[0].scrollHeight);
				if (done) {
					frappe.realtime.off("dms.key.sync.all.timesheet");
					this.togglegetTimesheet(false);
					this.syncRunning = false;
				}
			}
		);
	}
	togglegetKPI(disable = true) {
		const btn = $("#btn-get-dms-kpi");

		const _toggleClass = (d) => (d ? "btn-success" : "btn-primary");
		const _toggleText = () => (disable ? "Syncing..." : "Lấy dữ liệu KPI");

		btn.prop("disabled", disable)
			.addClass(_toggleClass(disable))
			.removeClass(_toggleClass(!disable))
			.text(_toggleText());
	}

	togglegetTimesheet(disable = true) {
		const btn = $("#btn-get-dms-timesheet");

		const _toggleClass = (d) => (d ? "btn-success" : "btn-primary");
		const _toggleText = () => (disable ? "Syncing..." : "Lấy dữ liệu bảng công");

		btn.prop("disabled", disable)
			.addClass(_toggleClass(disable))
			.removeClass(_toggleClass(!disable))
			.text(_toggleText());
	}

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
			() => this.addTable(1),
			() => this.checkSyncStatus(),
			() => this.listen(),
		]);
	}

	async checkSyncStatus() {
		const jobs = await frappe.db.get_list("RQ Job", {
			filters: { status: ("in", ("queued", "started")) },
		});

		// console.log("Fetched Jobs:", jobs);

		const filteredJobs = jobs.filter((job) =>
			["queued", "started"].includes(job.status)
		);

		// console.log("Filtered Jobs:", filteredJobs);
		this.syncRunning = filteredJobs.find(
			(job) =>
				job.job_name ===
				"mbw_integration_dms.mbw_integration_dms.product.sync_product_job"
		);

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
                        <h5 class="border-bottom pb-2">Products in ERPNext</h5>
                        <div id="dms-product-list">
                            <div class="text-center">Loading...</div>
                        </div>
                        <div class="dms-datatable-footer mt-2 pt-3 pb-2 border-top text-right" style="display: none">
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-prev-product">Prev</button>
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-next-product">Next</button>
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
                                    <button type="button" id="btn-sync-all-product" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Sync all Products</button>
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
		const data = await this.fetchdmsProducts();
		this.dmsProductTable = new frappe.DataTable(listElement, {
			columns: [
				{
					name: "Item Code",
					align: "left",
					editable: false,
					focusable: false,
					width: 250,
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
			],
			data: await this.fetchdmsProducts(),
			layout: "fixed",
		});
		if (data.length === 0) {
			let scrollable = this.wrapper.find("#dms-product-list .dt-scrollable")[0];
			scrollable.style.height = "auto";
		}
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
			this.next_page = products.length > 0 ? page + 1 : page;
			this.prev_page = page > 1 ? page - 1 : page;

			const dmsProducts = products.map((product) => ({
				// 'Image': product.image && product.image.src && `<img style="height: 50px" src="${product.image.src}">`,
				"Item Code": product.item_code,
				"Item Name": product.item_name,
				Status: this.getProductSyncStatus(product.is_sync),
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
		this.wrapper.on("click", ".btn-sync-product", (e) => {
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
		this.wrapper.on("click", ".btn-prev-product,.btn-next-product", (e) =>
			this.switchPage(e)
		);

		// sync all products
		this.wrapper.on("click", "#btn-sync-all-product", (e) => this.syncAll(e));
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
			_this.hasClass("btn-next-product") ? this.next_page : this.prev_page
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
		this.logSync();
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
					this.fetchdmsProducts();
					this.syncRunning = false;
				}
			}
		);
	}

	toggleSyncAllButton(disable = true) {
		const btn = $("#btn-sync-all-product");

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

//Show Category
CategoryImporter = class {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");
		this.log_category = 0
		this.init();
		this.syncRunning = false;
	}

	init() {
		frappe.run_serially([
			() => this.addMarkup(),
			() => this.fetchCategoryCount(),
			() => this.addTable(1),
			() => this.checkSyncStatus(),
			() => this.listen(),
		]);
	}

	async checkSyncStatus() {
		const jobs = await frappe.db.get_list("RQ Job", {
			filters: { status: ("in", ("queued", "started")) },
		});

		// console.log("Fetched Jobs:", jobs);

		const filteredJobs = jobs.filter((job) =>
			["queued", "started"].includes(job.status)
		);

		// console.log("Filtered Jobs:", filteredJobs);

		let list_job = ["mbw_integration_dms.mbw_integration_dms.brand.sync_brand_job",
			"mbw_integration_dms.mbw_integration_dms.channel.sync_channel_job",
			"mbw_integration_dms.mbw_integration_dms.customer.sync_customer_type_job",
			"mbw_integration_dms.mbw_integration_dms.customer.sync_customer_group_job",
			"mbw_integration_dms.mbw_integration_dms.industry.sync_industry_job",
			"mbw_integration_dms.mbw_integration_dms.provider.sync_provider_job",
			"mbw_integration_dms.mbw_integration_dms.region.sync_region_job",
			"mbw_integration_dms.mbw_integration_dms.unit.sync_unit_job",
			"mbw_integration_dms.mbw_integration_dms.warehouse.sync_warehouse_job"
		]
		this.syncRunning = filteredJobs.find(
			(job) =>
				list_job.includes(job.job_name)
		);

		if (this.syncRunning) {
			this.toggleSyncAllButton();
			// this.logSync();
		}
	}

	addMarkup() {
		const _markup = $(`
            <div class="row">
                <div class="col-lg-8 d-flex align-items-stretch">
                    <div class="card border-0 shadow-sm p-3 mb-3 w-100 rounded-sm" style="background-color: var(--card-bg)">
                        <h5 class="border-bottom pb-2">Category in ERPNext</h5>
                        <div id="dms-category-list">
                            <div class="text-center">Loading...</div>
                        </div>
                        <div class="dms-datatable-footer mt-2 pt-3 pb-2 border-top text-right" style="display: none">
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-prev-category">Prev</button>
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-next-category">Next</button>
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
                                    <button type="button" id="btn-sync-all-category" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Sync all Categories</button>
                                </div>
                                <div class="category-count py-3 d-flex justify-content-stretch">
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-categories-erpnext">-</h2>
                                        <p class="text-muted m-0">in ERPNext</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-categories-pending">-</h2>
                                        <p class="text-muted m-0">Pending Sync</p>
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
                            <div class="control-value like-disabled-input for-description overflow-auto" id="dms-sync-log-categories" style="max-height: 500px;"></div>
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
				message: { erpnextCount, pendingCount, syncedCount },
			} = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.get_count_categories",
			});
			console.log(erpnextCount)

			this.wrapper.find("#count-categories-pending").text(pendingCount);
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
					width: 250,
				},
				{
					name: "Category",
					editable: false,
					focusable: false,
					width: 150,
				},
				{
					name: "Doctype",
					align: "center",
					editable: false,
					focusable: false,
					width: 150,
				},
				{
					name: "Status",
					align: "center",
					editable: false,
					focusable: false,
					width: 150,
				},
			],
			data: await this.fetchdmsCategories(),
			layout: "fixed",
		});
		const data = await this.fetchdmsCategories()
		if (data.length === 0) {
			let scrollable = this.wrapper.find("#dms-category-list .dt-scrollable")[0];
			scrollable.style.height = "auto";
		}
		this.wrapper.find(".dms-datatable-footer").show();
	}

	async fetchdmsCategories(page=1) {
		try {
			const {
				message: categories }
			  = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.get_categories",
				args: { page: page},
			});
			this.next_page = categories.length > 0 ? page + 1 : page;
			this.prev_page = page > 1 ? page - 1 : page;
			const dmsCategories = categories.map((category) => ({
				// 'Image': category.image && category.image.src && `<img style="height: 50px" src="${category.image.src}">`,
				Name: category.name,
				Category: category.category,
				Doctype: category.doctype,
				Status: this.getCategoriesyncStatus(category.is_sync)
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
		this.wrapper.on("click", ".btn-prev-category,.btn-next-category", (e) =>
			this.switchPage(e)
		);

		// sync all categories
		this.wrapper.on("click", "#btn-sync-all-category", (e) => this.syncAll(e));
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
			_this.hasClass("btn-next-category") ? this.next_page : this.prev_page
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
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.sync_all_categories",
			});
		}
		this.log_category = 0;
		// sync progress
		this.logSync();
	}
	logSync() {
		const _log = $("#dms-sync-log-categories");
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
				this.log_category = this.log_category + 1;
				if (synced)
					this.updateSyncedCount(_syncedCounter, _erpnextCounter);

				if (done && this.log_category === 9) {
					frappe.realtime.off("dms.key.sync.all.categories");
					this.toggleSyncAllButton(false);
					this.fetchCategoryCount();
					this.fetchdmsCategories();
					this.syncRunning = false;
				}
			}
		);
	}

	toggleSyncAllButton(disable = true) {
		const btn = $("#btn-sync-all-category");

		const _toggleClass = (d) => (d ? "btn-success" : "btn-primary");
		const _toggleText = () => (disable ? "Syncing..." : "Sync Categories");

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

//Show Customer
CustomerImporter = class {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");
		this.page = wrapper.page;
		this.init();
		this.syncRunning = false;
	}

	init() {
		frappe.run_serially([
			() => this.addMarkup(),
			() => this.fetchCustomerCount(),
			() => this.addTable(1),
			() => this.checkSyncStatus(),
			() => this.listen(),
		]);
	}

	async checkSyncStatus() {
		const jobs = await frappe.db.get_list("RQ Job", {
			filters: { status: ("in", ("queued", "started")) },
		});

		// console.log("Fetched Jobs:", jobs);

		const filteredJobs = jobs.filter((job) =>
			["queued", "started"].includes(job.status)
		);

		// console.log("Filtered Jobs:", filteredJobs);
		this.syncRunning = filteredJobs.find(
			(job) =>
				job.job_name ===
				"mbw_integration_dms.mbw_integration_dms.customer.sync_customer_job"
		);

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
                        <h5 class="border-bottom pb-2">Customers in ERPNext</h5>
                        <div id="dms-customer-list">
                            <div class="text-center">Loading...</div>
                        </div>
                        <div class="dms-datatable-footer mt-2 pt-3 pb-2 border-top text-right" style="display: none">
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-prev-customer">Prev</button>
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-next-customer">Next</button>
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
                                    <button type="button" id="btn-sync-all-customer" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Sync all Customers</button>
                                </div>
                                <div class="customer-count py-3 d-flex justify-content-stretch">
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-customers-erpnext">-</h2>
                                        <p class="text-muted m-0">in ERPNext</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-customers-pending">-</h2>
                                        <p class="text-muted m-0">Pending sync</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-customers-synced">-</h2>
                                        <p class="text-muted m-0">Synced</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="card border-0 shadow-sm p-3 mb-3 rounded-sm" style="background-color: var(--card-bg); display: none;">
                            <h5 class="border-bottom pb-2">Sync Log</h5>
                            <div class="control-value like-disabled-input for-description overflow-auto" id="dms-sync-log-customers" style="max-height: 500px;"></div>
                        </div>

                    </div>
                </div>
            </div>
        `);

		this.wrapper.append(_markup);
	}

	async fetchCustomerCount() {
		try {
			const {
				message: { erpnextCount, pendingCount, syncedCount },
			} = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.get_count_customers",
			});

			this.wrapper.find("#count-customers-pending").text(pendingCount);
			this.wrapper.find("#count-customers-erpnext").text(erpnextCount);
			this.wrapper.find("#count-customers-synced").text(syncedCount);
		} catch (error) {
			frappe.throw(__("Error fetching customers count."));
		}
	}

	async addTable() {
		const listElement = this.wrapper.find("#dms-customer-list")[0];
		this.dmsCustomerTable = new frappe.DataTable(listElement, {
			columns: [
				{
					name: "Customer Name",
					align: "left",
					editable: false,
					focusable: false,
					width: 200,
				},
				{
					name: "Customer Code DMS",
					align: "left",
					editable: false,
					focusable: false,
					width: 200,
				},
				{
					name: "Email ID",
					align: "left",
					editable: false,
					focusable: false,
					width: 200,
				},
				{
					name: "Status",
					align: "center",
					editable: false,
					focusable: false,
					width: 150,
				},
			],
			data: await this.fetchdmsCustomers(),
			layout: "fixed",
		});
		const data = await this.fetchdmsCustomers();
		if (data.length === 0) {
			let scrollable = this.wrapper.find("#dms-customer-list .dt-scrollable")[0];
			scrollable.style.height = "auto";
		}
		this.wrapper.find(".dms-datatable-footer").show();
	}

	async fetchdmsCustomers(page = 1) {
		try {
			const {
				message: customers,
			} = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.get_customers",
				args: { page },
			});
			this.next_page = customers.length > 0 ? page + 1 : page;
			this.prev_page = page > 1 ? page - 1 : page;
			const dmsCustomers = customers.map((customer) => ({
				// 'Image': product.image && product.image.src && `<img style="height: 50px" src="${product.image.src}">`,
				"Customer Code DMS": customer.customer_code_dms,
				"Customer Name": customer.customer_name,
				"Email ID": customer.email_id,
				Status: this.getCustomerSyncStatus(customer.is_sync),
			}));

			return dmsCustomers;
		} catch (error) {
			frappe.throw(__("Error fetching customers."));
		}
	}

	getCustomerSyncStatus(status) {
		return status
			? `<span class="indicator-pill green">Synced</span>`
			: `<span class="indicator-pill orange">Not Synced</span>`;
	}

	listen() {
		// sync a product from table
		this.wrapper.on("click", ".btn-sync-customer", (e) => {
			const _this = $(e.currentTarget);

			_this.prop("disabled", true).text("Syncing...");

			const customer = _this.attr("data-customer");
			this.syncCustomer(customer).then((status) => {
				if (!status) {
					frappe.throw(__("Error syncing customer"));
					_this.prop("disabled", false).text("Sync");
					return;
				}

				_this
					.parents(".dt-row")
					.find(".indicator-pill")
					.replaceWith(this.getCustomerSyncStatus(true));

				_this.replaceWith(
					`<button type="button" class="btn btn-default btn-xs btn-resync mx-2" data-customer="${customer}"> Re-sync </button>`
				);
			});
		});

		this.wrapper.on("click", ".btn-resync", (e) => {
			const _this = $(e.currentTarget);

			_this.prop("disabled", true).text("Syncing...");

			const customer = _this.attr("data-customer");
			this.resyncCustomer(product)
				.then((status) => {
					if (!status) {
						frappe.throw(__("Error syncing customer"));
						return;
					}

					_this
						.parents(".dt-row")
						.find(".indicator-pill")
						.replaceWith(this.getCustomerSyncStatus(true));

					_this.prop("disabled", false).text("Re-sync");
				})
				.catch((ex) => {
					_this.prop("disabled", false).text("Re-sync");
					frappe.throw(__("Error syncing Product"));
				});
		});

		// pagination
		this.wrapper.on("click", ".btn-prev-customer,.btn-next-customer", (e) =>
			this.switchPage(e)
		);

		// sync all products
		this.wrapper.on("click", "#btn-sync-all-customer", (e) => this.syncAll(e));
	}

	async syncCustomer(product) {
		const { message: status } = await frappe.call({
			method: "dms_import_products.dms_import_products.sync_product",
			args: { product },
		});

		if (status) this.fetchCustomerCount();

		return status;
	}

	async resyncCustomer(product) {
		const { message: status } = await frappe.call({
			method: "dms_import_products.dms_import_products.resync_product",
			args: { product },
		});

		if (status) this.fetchCustomerCount();

		return status;
	}

	async switchPage({ currentTarget }) {
		const _this = $(currentTarget);

		$(".btn-paginate").prop("disabled", true);
		this.dmsCustomerTable.showToastMessage("Loading...");

		const newCustomers = await this.fetchdmsCustomers(
			_this.hasClass("btn-next-customer") ? this.next_page : this.prev_page
		);

		this.dmsCustomerTable.refresh(newCustomers);

		$(".btn-paginate").prop("disabled", false);
		this.dmsCustomerTable.clearToastMessage();
	}

	syncAll() {
		this.checkSyncStatus();
		this.toggleSyncAllButton();

		if (this.syncRunning) {
			frappe.msgprint(__("Sync already in progress"));
		} else {
			frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.sync_all_customers",
			});
		}

		// sync progress
		this.logSync();
	}
	toggleSyncAllButton(disable = true) {
		const btn = $("#btn-sync-all-customer");

		const _toggleClass = (d) => (d ? "btn-success" : "btn-primary");
		const _toggleText = () => (disable ? "Syncing..." : "Sync Customers");

		btn.prop("disabled", disable)
			.addClass(_toggleClass(disable))
			.removeClass(_toggleClass(!disable))
			.text(_toggleText());
	}

	logSync() {
		const _log = $("#dms-sync-log-customers");
		_log.parents(".card").show();
		_log.text(""); // clear logs

		// define counters here to prevent calling jquery every time
		const _syncedCounter = $("#count-customers-synced");
		const _erpnextCounter = $("#count-customers-erpnext");

		frappe.realtime.on(
			"dms.key.sync.all.customers",
			({ message, synced, done, error }) => {
				message = `<pre class="mb-0">${message}</pre>`;
				_log.append(message);
				_log.scrollTop(_log[0].scrollHeight);

				if (synced)
					this.updateSyncedCount(_syncedCounter, _erpnextCounter);

				if (done) {
					frappe.realtime.off("dms.key.sync.all.customers");
					this.toggleSyncAllButton(false);
					this.fetchCustomerCount();
					this.fetchdmsCustomers();
					this.syncRunning = false;
				}
			}
		);
	}

	updateSyncedCount(_syncedCounter, _erpnextCounter) {
		let _synced = parseFloat(_syncedCounter.text());
		let _erpnext = parseFloat(_erpnextCounter.text());

		_syncedCounter.text(_synced + 1);
		_erpnextCounter.text(_erpnext + 1);
	}
};

// Sync Sales Order
SalesOrderImporter = class {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find(".layout-main-section");
		this.page = wrapper.page;
		this.init();
		this.syncRunning = false;
	}

	init() {
		frappe.run_serially([
			() => this.addMarkup(),
			() => this.fetchSalesOrderCount(),
			() => this.addTable(1),
			() => this.checkSyncStatus(),
			() => this.listen(),
		]);
	}

	async checkSyncStatus() {
		const jobs = await frappe.db.get_list("RQ Job", {
			filters: { status: ("in", ("queued", "started")) },
		});

		// console.log("Fetched Jobs:", jobs);

		const filteredJobs = jobs.filter((job) =>
			["queued", "started"].includes(job.status)
		);

		// console.log("Filtered Jobs:", filteredJobs);
		this.syncRunning = filteredJobs.find(
			(job) =>
				job.job_name ===
				"mbw_integration_dms.mbw_integration_dms.customer.sync_customer_job"
		);

		if (this.syncRunning) {
			this.toggleSyncAllButton();
			// this.logSync();
		}
	}

	addMarkup() {
		const _markup = $(`
            <div class="row">
                <div class="col-lg-8 d-flex align-items-stretch">
                    <div class="card border-0 shadow-sm p-3 mb-3 w-100 rounded-sm" style="background-color: var(--card-bg)">
                        <h5 class="border-bottom pb-2">Sales Orders in ERPNext</h5>
                        <div id="dms-sales-order-list">
                            <div class="text-center">Loading...</div>
                        </div>
                        <div class="dms-datatable-footer mt-2 pt-3 pb-2 border-top text-right" style="display: none">
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-prev-sales-order">Prev</button>
                                <button type="button" class="btn btn-sm btn-default btn-paginate btn-next-sales-order">Next</button>
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
                                    <button type="button" id="btn-sync-all-sales-order" class="btn btn-xl btn-primary w-100 font-weight-bold py-3">Sync all Sales Orders</button>
                                </div>
                                <div class="customer-count py-3 d-flex justify-content-stretch">
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-sales-orders-erpnext">-</h2>
                                        <p class="text-muted m-0">in ERPNext</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-sales-orders-pending">-</h2>
                                        <p class="text-muted m-0">Pending sync</p>
                                    </div>
                                    <div class="text-center p-3 mx-2 rounded w-100" style="background-color: var(--bg-color)">
                                        <h2 id="count-sales-orders-synced">-</h2>
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

	async fetchSalesOrderCount() {
		try {
			const {
				message: { erpnextCount, pendingCount, syncedCount },
			} = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.get_count_customers",
			});

			this.wrapper.find("#count-sales-orders-pending").text(pendingCount);
			this.wrapper.find("#count-sales-orders-erpnext").text(erpnextCount);
			this.wrapper.find("#count-sales-orders-synced").text(syncedCount);
		} catch (error) {
			frappe.throw(__("Error fetching sales-orders count."));
		}
	}

	async addTable() {
		const listElement = this.wrapper.find("#dms-sales-order-list")[0];
		this.dmsSalesOrderTable = new frappe.DataTable(listElement, {
			columns: [
				{
					name: "Sales Order",
					align: "left",
					editable: false,
					focusable: false,
					width: 200,
				},
				{
					name: "Status",
					align: "center",
					editable: false,
					focusable: false,
					width: 120,
				},
			],
			data: await this.fetchdmsSalesOrders(),
			layout: "fixed",
		});

		this.wrapper.find(".dms-datatable-footer").show();
	}

	async fetchdmsSalesOrders(page = 1) {
		try {
			const {
				message: sales_orders,
			} = await frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_products.get_sales_orders",
				args: { page },
			});
			this.next_page = sales_orders.length > 0 ? page + 1 : page;
			this.prev_page = page > 1 ? page - 1 : page;
			const dmsSalesOrders = sales_orders.map((sales_order) => ({
				// 'Image': product.image && product.image.src && `<img style="height: 50px" src="${product.image.src}">`,
				"Sales Order": sales_order.name,
				Status: this.getSalesOrderSyncStatus(sales_order.is_sync),
			}));

			return dmsSalesOrders;
		} catch (error) {
			frappe.throw(__("Error fetching customers."));
		}
	}

	getSalesOrderSyncStatus(status) {
		return status
			? `<span class="indicator-pill green">Synced</span>`
			: `<span class="indicator-pill orange">Not Synced</span>`;
	}

	listen() {
		// sync a product from table
		this.wrapper.on("click", ".btn-sync-sales-order", (e) => {
			const _this = $(e.currentTarget);

			_this.prop("disabled", true).text("Syncing...");

			const sales_order = _this.attr("data-sales-order");
			this.syncSalesOrder(sales_order).then((status) => {
				if (!status) {
					frappe.throw(__("Error syncing sales order"));
					_this.prop("disabled", false).text("Sync");
					return;
				}

				_this
					.parents(".dt-row")
					.find(".indicator-pill")
					.replaceWith(this.getSalesOrderSyncStatus(true));

				_this.replaceWith(
					`<button type="button" class="btn btn-default btn-xs btn-resync mx-2" data-sales-order="${sales_order}"> Re-sync </button>`
				);
			});
		});

		// pagination
		this.wrapper.on("click", ".btn-prev-sales-order,.btn-next-sales-order", (e) =>
			this.switchPage(e)
		);

		// sync all products
		this.wrapper.on("click", "#btn-sync-all-sales-order", (e) => this.syncAll(e));
	}

	async syncSalesOrder(product) {
		const { message: status } = await frappe.call({
			method: "dms_import_products.dms_import_products.sync_product",
			args: { product },
		});

		if (status) this.fetchSalesOrderCount();

		return status;
	}

	async switchPage({ currentTarget }) {
		const _this = $(currentTarget);

		$(".btn-paginate").prop("disabled", true);
		this.dmsSalesOrderTable.showToastMessage("Loading...");

		const newSalesOrders = await this.fetchdmsSalesOrders(
			_this.hasClass("btn-next-sales-order") ? this.next_page : this.prev_page
		);

		this.dmsSalesOrderTable.refresh(newSalesOrders);

		$(".btn-paginate").prop("disabled", false);
		this.dmsSalesOrderTable.clearToastMessage();
	}

	syncAll() {
		this.checkSyncStatus();
		this.toggleSyncAllButton();

		if (this.syncRunning) {
			frappe.msgprint(__("Sync already in progress"));
		} else {
			frappe.call({
				method: "mbw_integration_dms.mbw_integration_dms.page.dms_import_products.dms_import_category.sync_all_customers",
			});
		}

		// sync progress
		// this.logSync();
	}
	toggleSyncAllButton(disable = true) {
		const btn = $("#btn-sync-all-sales-order");

		const _toggleClass = (d) => (d ? "btn-success" : "btn-primary");
		const _toggleText = () => (disable ? "Syncing..." : "Sync Sales Order");

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