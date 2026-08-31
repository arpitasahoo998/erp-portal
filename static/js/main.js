/* ================================================================
   SPICE BITES – Main JavaScript
   ================================================================ */

// ── Flash message auto-dismiss ──────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash').forEach(el => {
        el.addEventListener('click', () => el.remove());
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateX(40px)';
            setTimeout(() => el.remove(), 400);
        }, 4000);
    });
});

// ── Sidebar mobile toggle ───────────────────────────────────────
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
}

// ── Purchase form: add / remove items ───────────────────────────
let purchaseItemCount = 0;

function addPurchaseItem() {
    const container = document.getElementById('purchase-items');
    if (!container) return;

    const html = `
    <div class="item-row" id="purchase-item-${purchaseItemCount}" style="display:flex; flex-wrap:wrap; gap: 10px;">
        <div class="form-group" style="flex: 2; min-width: 150px;">
            <label>Product Name</label>
            <input type="text" name="product_name_${purchaseItemCount}" class="form-control"
                   list="product-datalist" placeholder="Product name" required>
        </div>
        <div class="form-group" style="flex: 1; min-width: 80px;">
            <label>HSN</label>
            <input type="text" name="hsn_code_${purchaseItemCount}" class="form-control" placeholder="HSN">
        </div>
        <div class="form-group" style="flex: 1; min-width: 80px;">
            <label>Unit/Bag</label>
            <input type="text" name="unit_${purchaseItemCount}" class="form-control" value="PCS" placeholder="Unit">
        </div>
        <div class="form-group" style="flex: 1; min-width: 60px;">
            <label>Qty</label>
            <input type="number" name="quantity_${purchaseItemCount}" class="form-control"
                   min="1" value="1" required>
        </div>
        <div class="form-group" style="flex: 1; min-width: 80px;">
            <label>Rate</label>
            <input type="number" name="purchase_price_${purchaseItemCount}" class="form-control"
                   step="0.01" min="0" required placeholder="Price">
        </div>
        <div class="form-group" style="flex: 1; min-width: 60px;">
            <label>GST%</label>
            <input type="number" name="gst_rate_${purchaseItemCount}" class="form-control" step="0.1" value="0" min="0">
        </div>
        <div class="form-group" style="flex: 1; min-width: 80px;">
            <label>Selling Price</label>
            <input type="number" name="selling_price_${purchaseItemCount}" class="form-control"
                   step="0.01" min="0" required>
        </div>
        <div class="form-group" style="flex: 1; min-width: 100px;">
            <label>Batch</label>
            <input type="text" name="batch_no_${purchaseItemCount}" class="form-control" placeholder="Batch No">
        </div>
        <div class="form-group" style="flex: 1; min-width: 80px;">
            <label>Amount</label>
            <input type="number" id="amt_${purchaseItemCount}" class="form-control" readonly style="background:transparent; font-weight:700; color:var(--accent-light);">
        </div>
        <button type="button" class="remove-item" style="height: fit-content; margin-top: 30px;" onclick="removePurchaseItem(${purchaseItemCount})">✕</button>
    </div>`;
    container.insertAdjacentHTML('beforeend', html);
    purchaseItemCount++;
    document.getElementById('item_count').value = purchaseItemCount;
}

function removePurchaseItem(idx) {
    const el = document.getElementById(`purchase-item-${idx}`);
    if (el) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(-10px)';
        setTimeout(() => el.remove(), 300);
    }
}

// ── Billing form: add / remove sale items ───────────────────────
let saleItemCount = 0;

function addSaleItem() {
    const container = document.getElementById('sale-items');
    if (!container) return;

    const html = `
    <div class="item-row item-row-billing" id="sale-item-${saleItemCount}">
        <div class="form-group">
            <label>Product</label>
            <select name="product_id_${saleItemCount}" class="form-control"
                    onchange="loadBatches(${saleItemCount}, this.value)" required>
                <option value="">Select product</option>
            </select>
        </div>
        <div class="form-group">
            <label>Batch</label>
            <select name="batch_id_${saleItemCount}" class="form-control"
                    onchange="setBatchPrice(${saleItemCount}, this)" required>
                <option value="">Select batch</option>
            </select>
        </div>
        <div class="form-group">
            <label>Qty</label>
            <input type="number" name="qty_${saleItemCount}" class="form-control"
                   min="1" value="1" onchange="calcItemAmount(${saleItemCount})"
                   oninput="calcItemAmount(${saleItemCount})" required>
        </div>
        <div class="form-group">
            <label>Price</label>
            <input type="number" name="price_${saleItemCount}" class="form-control"
                   step="0.01" min="0" onchange="calcItemAmount(${saleItemCount})"
                   oninput="calcItemAmount(${saleItemCount})" required>
        </div>
        <div class="form-group">
            <label>Amount</label>
            <input type="text" class="form-control" id="amount_${saleItemCount}"
                   readonly style="background:transparent; font-weight:700; color:var(--accent-light);">
        </div>
        <button type="button" class="remove-item" onclick="removeSaleItem(${saleItemCount})">✕</button>
    </div>`;
    container.insertAdjacentHTML('beforeend', html);

    // populate products dropdown
    const sel = container.querySelector(`#sale-item-${saleItemCount} select[name="product_id_${saleItemCount}"]`);
    fetch('/api/products')
        .then(r => r.json())
        .then(products => {
            products.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.name} (Stock: ${p.stock})`;
                sel.appendChild(opt);
            });
        });

    saleItemCount++;
    document.getElementById('sale_item_count').value = saleItemCount;
}

function removeSaleItem(idx) {
    const el = document.getElementById(`sale-item-${idx}`);
    if (el) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            el.remove();
            calcGrandTotal();
        }, 300);
    }
}

function loadBatches(idx, productId) {
    const batchSel = document.querySelector(`select[name="batch_id_${idx}"]`);
    batchSel.innerHTML = '<option value="">Select batch</option>';
    if (!productId) return;

    fetch(`/api/products/${productId}/batches`)
        .then(r => r.json())
        .then(batches => {
            batches.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.id;
                opt.dataset.price = b.selling_price;
                opt.dataset.stock = b.remaining_qty;
                let label = `${b.batch_no || 'N/A'} | Stock: ${b.remaining_qty} | ₹${b.selling_price}`;
                if (b.expiry_date) label += ` | Exp: ${b.expiry_date}`;
                opt.textContent = label;
                batchSel.appendChild(opt);
            });
        });
}

function setBatchPrice(idx, selectEl) {
    const opt = selectEl.selectedOptions[0];
    if (opt && opt.dataset.price) {
        document.querySelector(`input[name="price_${idx}"]`).value = opt.dataset.price;
        const qtyInput = document.querySelector(`input[name="qty_${idx}"]`);
        qtyInput.max = opt.dataset.stock;
        calcItemAmount(idx);
    }
}

function calcItemAmount(idx) {
    const qty = parseFloat(document.querySelector(`input[name="qty_${idx}"]`)?.value) || 0;
    const price = parseFloat(document.querySelector(`input[name="price_${idx}"]`)?.value) || 0;
    const amount = qty * price;
    const amountEl = document.getElementById(`amount_${idx}`);
    if (amountEl) amountEl.value = `₹${amount.toFixed(2)}`;
    calcGrandTotal();
}

function calcGrandTotal() {
    let subtotal = 0;
    document.querySelectorAll('[id^="amount_"]').forEach(el => {
        const val = parseFloat(el.value.replace('₹', '').replace(/,/g, '')) || 0;
        subtotal += val;
    });
    const discount = parseFloat(document.getElementById('discount')?.value) || 0;
    const totalEl = document.getElementById('grand-total');
    if (totalEl) {
        totalEl.textContent = `₹${(subtotal - discount).toFixed(2)}`;
    }
    const subtotalEl = document.getElementById('subtotal-display');
    if (subtotalEl) {
        subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
    }
}

// ── Payment modal ───────────────────────────────────────────────
function openPaymentModal(paymentId, status, amount, followup, paymentDate, remarks) {
    const modal = document.getElementById('payment-modal');
    if (!modal) return;

    document.getElementById('modal-payment-id').value = paymentId;
    document.getElementById('modal-status').value = status || 'Pending';
    document.getElementById('modal-amount').value = amount || 0;
    document.getElementById('modal-followup').value = followup || '';
    document.getElementById('modal-payment-date').value = paymentDate || '';
    document.getElementById('modal-remarks').value = remarks || '';

    // set form action
    document.getElementById('payment-form').action = `/payments/update/${paymentId}`;

    modal.classList.add('active');
}

function closePaymentModal() {
    document.getElementById('payment-modal')?.classList.remove('active');
}

// close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});

// ── Dashboard chart ─────────────────────────────────────────────
function initDashboardChart(labels, data) {
    const ctx = document.getElementById('salesChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sales (₹)',
                data: data,
                backgroundColor: 'rgba(99, 102, 241, 0.5)',
                borderColor: 'rgba(99, 102, 241, 1)',
                borderWidth: 2,
                borderRadius: 6,
                hoverBackgroundColor: 'rgba(99, 102, 241, 0.7)',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 15, 42, 0.95)',
                    titleColor: '#e2e8f0',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(99, 102, 241, 0.3)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        label: function(ctx) {
                            return `₹${ctx.parsed.y.toLocaleString('en-IN')}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#64748b', font: { size: 11 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: {
                        color: '#64748b',
                        font: { size: 11 },
                        callback: v => '₹' + v.toLocaleString('en-IN')
                    }
                }
            }
        }
    });
}
