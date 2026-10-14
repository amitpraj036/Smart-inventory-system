    let inventory = [];
    let stockLogs = [];
    let invoices = [];
    let bestSellers = [];
    let cart = [];
    let lastReceiptData = null;
    let catalogView = 'grid';
    let selectedCategory = 'ALL';

    async function fetchFullState() {
      try {
        const res = await fetch('/api/state');
        const data = await res.json();
        inventory = data.inventory || [];
        stockLogs = data.stockLogs || [];
        invoices = data.invoices || [];
        bestSellers = data.bestSellers || [];

        // DB Badge
        const dbBadge = document.getElementById('dbBadge');
        if (data.dbStatus?.isPostgres) {
          dbBadge.textContent = '🐘 PostgreSQL Live';
          dbBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-mono bg-indigo-900/80 text-indigo-200 border border-indigo-400/50';
        } else {
          dbBadge.textContent = '💾 SQLite Persistent';
          dbBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-500/30';
        }

        renderCategoryPills();
        renderInventoryCards();
        renderPosOptions();
        renderAuditLogs();
        renderBestSellers();
        renderKpis();
        checkLowStockAlerts();
      } catch (err) {
        showToast("Error connecting to server backend");
      }
    }

    function checkLowStockAlerts() {
      const lowItems = inventory.filter(p => p.stock <= p.reorder);
      const banner = document.getElementById('alertBanner');
      const text = document.getElementById('alertBannerText');
      if (lowItems.length > 0) {
        const names = lowItems.slice(0, 3).map(i => `${i.name} (${i.stock} left)`).join(', ');
        text.textContent = `Low stock on ${lowItems.length} item(s): ${names}${lowItems.length > 3 ? '...' : ''}`;
        banner.classList.remove('hidden');
      } else {
        banner.classList.add('hidden');
      }
    }

    function renderKpis() {
      const valuation = inventory.reduce((acc, p) => acc + (p.price * p.stock), 0);
      const totalUnits = inventory.reduce((acc, p) => acc + p.stock, 0);
      const totalRev = invoices.reduce((acc, i) => acc + i.total, 0);

      document.getElementById('statValuation').textContent = `₹${valuation.toFixed(2)}`;
      document.getElementById('statUnits').textContent = totalUnits;
      document.getElementById('statOrders').textContent = invoices.length;
      document.getElementById('statRevenue').textContent = `₹${totalRev.toFixed(2)}`;
    }

    function switchCatalogView(mode) {
      catalogView = mode;
      const cardsCont = document.getElementById('productCardsContainer');
      const tableCont = document.getElementById('productTableContainer');
      const gridBtn = document.getElementById('viewGridBtn');
      const listBtn = document.getElementById('viewListBtn');

      if (mode === 'grid') {
        cardsCont.classList.remove('hidden');
        tableCont.classList.add('hidden');
        gridBtn.className = 'px-2.5 py-1 rounded-lg font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30';
        listBtn.className = 'px-2.5 py-1 rounded-lg font-medium text-slate-400 hover:text-white';
      } else {
        cardsCont.classList.add('hidden');
        tableCont.classList.remove('hidden');
        listBtn.className = 'px-2.5 py-1 rounded-lg font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30';
        gridBtn.className = 'px-2.5 py-1 rounded-lg font-medium text-slate-400 hover:text-white';
      }
      renderInventoryCards();
    }

    function setCategoryFilter(cat) {
      selectedCategory = cat;
      renderCategoryPills();
      renderInventoryCards();
    }

    function renderCategoryPills() {
      const pillsContainer = document.getElementById('categoryFilterPills');
      if (!pillsContainer) return;
      const categories = ['ALL', ...new Set(inventory.map(p => p.category))];

      pillsContainer.innerHTML = categories.map(cat => {
        const isActive = selectedCategory === cat;
        return `
          <button onclick="setCategoryFilter('${cat}')" class="px-2.5 py-1 rounded-xl font-medium whitespace-nowrap transition-all ${isActive ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20' : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-white/5'}">
            ${cat === 'ALL' ? '🌟 All Items' : cat}
          </button>
        `;
      }).join('');
    }

    function renderInventoryCards() {
      const q = (document.getElementById('catalogSearchInput')?.value || '').toLowerCase().trim();
      const filtered = inventory.filter(p => {
        const matchQuery = p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q) || p.category.toLowerCase().includes(q);
        const matchCategory = (selectedCategory === 'ALL' || p.category === selectedCategory);
        return matchQuery && matchCategory;
      });

      // 1. Render Card Boxes
      const cardContainer = document.getElementById('productCardsContainer');
      if (filtered.length === 0) {
        cardContainer.innerHTML = `
          <div class="col-span-full py-12 text-center text-slate-400 glass-panel rounded-2xl">
            <span class="text-3xl">🔍</span>
            <p class="mt-2 text-xs font-semibold">No products found matching filters</p>
          </div>
        `;
      } else {
        cardContainer.innerHTML = filtered.map(p => {
          const isLow = p.stock <= p.reorder;
          const isOut = p.stock <= 0;
          const statusBg = isOut ? 'bg-rose-950/80 text-rose-300 border-rose-500/30' : (isLow ? 'bg-amber-950/80 text-amber-300 border-amber-500/30' : 'bg-emerald-950/80 text-emerald-300 border-emerald-500/30');
          const statusLabel = isOut ? 'OUT OF STOCK' : (isLow ? 'LOW STOCK' : 'IN STOCK');
          
          const stockPct = Math.min(100, Math.max(5, (p.stock / Math.max(p.reorder * 2, 1)) * 100));
          const barColor = isOut ? 'bg-rose-500' : (isLow ? 'bg-amber-500' : 'bg-emerald-500');

          return `
            <div class="glass-panel rounded-2xl p-3.5 border ${isLow ? 'border-amber-500/30 bg-amber-950/10' : 'border-white/10'} hover:border-cyan-400/50 hover:shadow-lg hover:shadow-cyan-500/10 transition-all flex flex-col justify-between group">
              <div>
                <div class="flex items-start justify-between gap-2 mb-2.5">
                  <div class="flex items-center gap-2.5">
                    <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-950/90 to-blue-900/60 border border-cyan-500/30 flex items-center justify-center text-2xl shadow-inner group-hover:scale-105 transition-transform flex-shrink-0">
                      ${p.emoji || '📦'}
                    </div>
                    <div>
                      <h4 class="font-bold text-white text-xs md:text-sm line-clamp-1">${p.name}</h4>
                      <span class="inline-block mt-0.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/5 text-slate-300 border border-white/10">
                        ${p.category}
                      </span>
                    </div>
                  </div>
                  <span class="font-mono text-[10px] px-2 py-0.5 rounded-lg bg-cyan-950/80 text-cyan-300 font-bold border border-cyan-500/30">
                    ${p.id}
                  </span>
                </div>

                <div class="bg-black/25 rounded-xl p-2.5 border border-white/5 mb-3 space-y-1.5">
                  <div class="flex items-center justify-between">
                    <span class="text-[11px] text-slate-400">Unit Price</span>
                    <span class="font-mono font-bold text-sm text-cyan-300">₹${p.price.toFixed(2)}</span>
                  </div>

                  <div class="flex items-center justify-between">
                    <span class="text-[11px] text-slate-400">Available Qty</span>
                    <div class="flex items-center gap-1.5">
                      <span class="font-mono font-bold text-xs ${isOut ? 'text-rose-400' : (isLow ? 'text-amber-400' : 'text-emerald-400')}">
                        ${p.stock} units
                      </span>
                      <span class="text-[9px] px-1.5 py-0.2 rounded font-bold border ${statusBg}">
                        ${statusLabel}
                      </span>
                    </div>
                  </div>

                  <div class="w-full bg-white/5 h-1.5 rounded-full overflow-hidden mt-1">
                    <div class="h-full ${barColor} transition-all duration-300" style="width: ${stockPct}%"></div>
                  </div>
                  <div class="text-[9px] text-slate-500 text-right font-mono">Min alert: ${p.reorder} units</div>
                </div>
              </div>

              <div class="grid grid-cols-3 gap-1.5 pt-1">
                <button onclick="openEditProductModal('${p.id}')" class="px-2 py-1.5 rounded-xl bg-cyan-950/70 border border-cyan-500/30 text-cyan-300 text-[11px] font-semibold hover:bg-cyan-900/80 transition flex items-center justify-center gap-1">
                  <span>✏️</span> Edit
                </button>
                <button onclick="openRestockModal('${p.id}')" class="px-2 py-1.5 rounded-xl bg-emerald-950/70 border border-emerald-500/30 text-emerald-300 text-[11px] font-semibold hover:bg-emerald-900/80 transition flex items-center justify-center gap-1">
                  <span>+</span> Restock
                </button>
                <button onclick="quickAddToCart('${p.id}')" class="px-2 py-1.5 rounded-xl glass-btn-primary text-white text-[11px] font-bold transition flex items-center justify-center gap-1 shadow-sm">
                  <span>🛒</span> Add
                </button>
              </div>
            </div>
          `;
        }).join('');
      }

      // 2. Render Table View (if toggled)
      const tbody = document.getElementById('inventoryTableBody');
      if (tbody) {
        tbody.innerHTML = filtered.map(p => `
          <tr class="hover:bg-white/5 transition">
            <td class="px-3 py-2.5 font-mono text-cyan-400 font-bold">${p.id}</td>
            <td class="px-3 py-2.5 text-white font-medium">${p.emoji || '📦'} ${p.name}</td>
            <td class="px-3 py-2.5 text-slate-400">${p.category}</td>
            <td class="px-3 py-2.5 text-right font-mono">₹${p.price.toFixed(2)}</td>
            <td class="px-3 py-2.5 text-center font-bold ${p.stock <= p.reorder ? 'text-amber-400' : 'text-slate-200'}">${p.stock}</td>
            <td class="px-3 py-2.5 text-center">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${p.stock <= p.reorder ? 'bg-amber-950 text-amber-300 border border-amber-500/30' : 'bg-emerald-950 text-emerald-300 border border-emerald-500/30'}">
                ${p.stock <= p.reorder ? 'LOW' : 'OK'}
              </span>
            </td>
            <td class="px-3 py-2.5 text-center">
              <div class="flex items-center justify-center gap-1">
                <button onclick="openEditProductModal('${p.id}')" class="px-2 py-1 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-[10px]">✏️</button>
                <button onclick="openRestockModal('${p.id}')" class="px-2 py-1 rounded-lg bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-[10px]">+Stock</button>
                <button onclick="quickAddToCart('${p.id}')" class="px-2 py-1 rounded-lg bg-blue-600/70 text-white text-[10px]">🛒</button>
              </div>
            </td>
          </tr>
        `).join('');
      }
    }

    function quickAddToCart(productId) {
      const prod = inventory.find(p => p.id === productId);
      if (!prod) return;
      if (prod.stock <= 0) {
        showToast(`Sorry, ${prod.name} is currently out of stock!`);
        return;
      }
      const inCart = cart.find(c => c.id === productId);
      const currentQty = inCart ? inCart.qty : 0;
      if (currentQty + 1 > prod.stock) {
        showToast(`Cannot add. Only ${prod.stock} total units in stock!`);
        return;
      }
      if (inCart) {
        inCart.qty += 1;
        inCart.lineTotal = inCart.qty * inCart.price;
      } else {
        cart.push({
          id: prod.id,
          name: prod.name,
          price: prod.price,
          qty: 1,
          lineTotal: prod.price
        });
      }
      renderCart();
      showToast(`Added 1x ${prod.name} to POS Cart!`);
    }

    function renderPosOptions() {
      const select = document.getElementById('posItemSelect');
      const inStock = inventory.filter(p => p.stock > 0);
      select.innerHTML = inStock.map(p => `
        <option value="${p.id}">${p.emoji || '📦'} ${p.name} — ₹${p.price.toFixed(2)} (${p.stock} avail)</option>
      `).join('');
    }

    function renderAuditLogs() {
      const c = document.getElementById('stockLogsList');
      if (stockLogs.length === 0) {
        c.innerHTML = '<div class="text-slate-500 text-center py-4">No audit logs recorded yet.</div>';
        return;
      }
      c.innerHTML = stockLogs.map(l => `
        <div class="flex justify-between items-center p-2 rounded-xl bg-white/5 border border-white/5">
          <div>
            <div class="font-medium text-slate-200">${l.itemId} <span class="text-slate-400 font-normal font-mono text-[10px]">(${l.timestamp.split(' ')[1] || l.timestamp})</span></div>
            <div class="text-[10px] text-slate-400">${l.note}</div>
          </div>
          <span class="font-mono font-bold ${l.type.includes('IN') ? 'text-emerald-400' : (l.type.includes('EDIT') ? 'text-cyan-400' : 'text-amber-400')}">
            ${l.type.includes('IN') ? '+' : (l.type.includes('EDIT') ? '⚙' : '-')}${l.qty}
          </span>
        </div>
      `).join('');
    }

    function renderBestSellers() {
      const c = document.getElementById('bestSellersList');
      if (bestSellers.length === 0) {
        c.innerHTML = '<div class="text-slate-500 text-center py-4">No sales recorded yet.</div>';
        return;
      }
      const medals = ['🥇', '🥈', '🥉', '#4', '#5'];
      c.innerHTML = bestSellers.map((b, i) => `
        <div class="flex justify-between items-center p-2 rounded-xl bg-white/5 border border-white/5">
          <div class="flex items-center gap-2">
            <span>${medals[i] || '★'}</span>
            <span class="text-slate-200 font-medium">${b.name}</span>
          </div>
          <div class="text-right">
            <span class="text-emerald-400 font-mono font-bold">${b.qty} sold</span>
            <div class="text-[10px] text-slate-400 font-mono">₹${b.revenue.toFixed(2)}</div>
          </div>
        </div>
      `).join('');
    }

    // POS Cart Operations
    function addToCart() {
      const select = document.getElementById('posItemSelect');
      const qtyInput = document.getElementById('posQtyInput');
      const id = select.value;
      const qty = parseInt(qtyInput.value);
      if (!id || qty <= 0) return;

      const prod = inventory.find(p => p.id === id);
      if (!prod) return;

      const inCart = cart.find(c => c.id === id);
      const currentQty = inCart ? inCart.qty : 0;
      if (currentQty + qty > prod.stock) {
        showToast(`Cannot add. Only ${prod.stock - currentQty} more units in stock!`);
        return;
      }

      if (inCart) {
        inCart.qty += qty;
        inCart.lineTotal = inCart.qty * inCart.price;
      } else {
        cart.push({
          id: prod.id,
          name: prod.name,
          price: prod.price,
          qty: qty,
          lineTotal: qty * prod.price
        });
      }
      renderCart();
      showToast(`Added ${prod.name} to cart`);
    }

    function removeFromCart(id) {
      cart = cart.filter(c => c.id !== id);
      renderCart();
    }

    function clearCart() {
      cart = [];
      renderCart();
    }

    function renderCart() {
      const c = document.getElementById('cartItemsContainer');
      if (cart.length === 0) {
        c.innerHTML = '<div class="text-slate-500 text-center py-8">Your checkout cart is empty</div>';
      } else {
        c.innerHTML = cart.map(item => `
          <div class="flex items-center justify-between p-2 rounded-xl bg-white/5 border border-white/5">
            <div>
              <div class="font-bold text-white">${item.name}</div>
              <div class="text-[10px] text-slate-400 font-mono">₹${item.price.toFixed(2)} × ${item.qty}</div>
            </div>
            <div class="flex items-center gap-3">
              <span class="font-mono font-bold text-cyan-300">₹${item.lineTotal.toFixed(2)}</span>
              <button onclick="removeFromCart('${item.id}')" class="text-rose-400 hover:text-rose-300 text-xs p-1">✕</button>
            </div>
          </div>
        `).join('');
      }
      renderCartSummary();
    }

    function renderCartSummary() {
      const subtotal = cart.reduce((acc, c) => acc + c.lineTotal, 0);
      const discPct = parseFloat(document.getElementById('posDiscount').value || 0);
      const taxPct = parseFloat(document.getElementById('posTax').value || 0);

      const discAmt = subtotal * (discPct / 100);
      const taxable = subtotal - discAmt;
      const taxAmt = taxable * (taxPct / 100);
      const total = taxable + taxAmt;

      document.getElementById('posSubtotalTxt').textContent = `₹${subtotal.toFixed(2)}`;
      document.getElementById('posDiscountTxt').textContent = `-₹${discAmt.toFixed(2)}`;
      document.getElementById('posTaxTxt').textContent = `+₹${taxAmt.toFixed(2)}`;
      document.getElementById('posTotalTxt').textContent = `₹${total.toFixed(2)}`;
    }

    async function handleCheckout() {
      if (cart.length === 0) {
        showToast("Add items to your cart first!");
        return;
      }
      const customer = document.getElementById('custNameInput').value.trim() || 'Walk-in Student';
      const subtotal = cart.reduce((acc, c) => acc + c.lineTotal, 0);
      const discPct = parseFloat(document.getElementById('posDiscount').value || 0);
      const taxPct = parseFloat(document.getElementById('posTax').value || 0);
      const discAmt = subtotal * (discPct / 100);
      const taxable = subtotal - discAmt;
      const taxAmt = taxable * (taxPct / 100);
      const total = taxable + taxAmt;

      const payload = {
        customer,
        cart,
        subtotal,
        discount: discAmt,
        tax: taxAmt,
        total
      };

      const res = await fetch('/api/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await res.json();
      if (result.success) {
        showReceiptModal(result.invoiceId, customer, cart, subtotal, discAmt, taxAmt, total);
        cart = [];
        renderCart();
        fetchFullState();
        showToast("Order completed successfully!");
      } else {
        showToast("Checkout failed: " + result.message);
      }
    }

    function showReceiptModal(invId, customer, cartItems, sub, disc, tax, tot) {
      const now = new Date().toLocaleString();
      let receipt = `=====================================\n`;
      receipt += `      CAMPUS SMART STORE & CAFE      \n`;
      receipt += `         OFFICIAL TAX INVOICE        \n`;
      receipt += `=====================================\n`;
      receipt += `Invoice : ${invId}\n`;
      receipt += `Date    : ${now}\n`;
      receipt += `Customer: ${customer}\n`;
      receipt += `-------------------------------------\n`;
      receipt += `ITEM                 QTY     PRICE   \n`;
      receipt += `-------------------------------------\n`;
      cartItems.forEach(i => {
        const n = (i.name.length > 18 ? i.name.slice(0, 16) + '..' : i.name).padEnd(19);
        const q = String(i.qty).padStart(3);
        const p = ('₹' + i.lineTotal.toFixed(2)).padStart(10);
        receipt += `${n} ${q} ${p}\n`;
      });
      receipt += `-------------------------------------\n`;
      receipt += `Subtotal:                  ₹${sub.toFixed(2)}\n`;
      receipt += `Discount:                 -₹${disc.toFixed(2)}\n`;
      receipt += `Tax (GST):                +₹${tax.toFixed(2)}\n`;
      receipt += `=====================================\n`;
      receipt += `GRAND TOTAL:               ₹${tot.toFixed(2)}\n`;
      receipt += `=====================================\n`;
      receipt += `   Thank you for supporting us!      \n`;
      receipt += `   Dev: Amit Prajapat (Jaipur, IN)   \n`;

      lastReceiptData = { text: receipt, filename: `Receipt_${invId}.txt` };
      document.getElementById('receiptInvId').textContent = invId;
      document.getElementById('receiptText').textContent = receipt;
      document.getElementById('receiptModal').classList.remove('hidden');
    }

    function closeReceiptModal() {
      document.getElementById('receiptModal').classList.add('hidden');
    }

    function downloadReceiptTxt() {
      if (!lastReceiptData) return;
      const blob = new Blob([lastReceiptData.text], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = lastReceiptData.filename;
      a.click();
    }

    // Product Modals
    function openNewProductModal() { document.getElementById('newProductModal').classList.remove('hidden'); }
    function closeNewProductModal() { document.getElementById('newProductModal').classList.add('hidden'); }

    function openEditProductModal(id) {
      const prod = inventory.find(p => p.id === id);
      if (!prod) return;

      document.getElementById('editProd_id').value = prod.id;
      document.getElementById('editProd_idBadge').textContent = prod.id;
      document.getElementById('editProd_name').value = prod.name;
      document.getElementById('editProd_cat').value = prod.category;
      document.getElementById('editProd_price').value = prod.price;
      document.getElementById('editProd_reorder').value = prod.reorder;
      document.getElementById('editProd_emoji').value = prod.emoji || '📦';

      document.getElementById('editProductModal').classList.remove('hidden');
    }

    function closeEditProductModal() {
      document.getElementById('editProductModal').classList.add('hidden');
    }

    async function handleEditProductSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('editProd_id').value;
      const name = document.getElementById('editProd_name').value.trim();
      const category = document.getElementById('editProd_cat').value.trim();
      const price = parseFloat(document.getElementById('editProd_price').value);
      const reorder = parseInt(document.getElementById('editProd_reorder').value);
      const emoji = document.getElementById('editProd_emoji').value.trim() || '📦';

      const res = await fetch('/api/products/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name, category, price, reorder, emoji })
      });
      const result = await res.json();
      if (result.success) {
        closeEditProductModal();
        fetchFullState();
        showToast("Item details updated successfully!");
      } else {
        showToast("Error updating: " + result.message);
      }
    }

    async function handleNewProductSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('newProd_id').value.trim().toUpperCase();
      const name = document.getElementById('newProd_name').value.trim();
      const category = document.getElementById('newProd_cat').value.trim();
      const emoji = document.getElementById('newProd_emoji').value.trim() || '📦';
      const price = parseFloat(document.getElementById('newProd_price').value);
      const stock = parseInt(document.getElementById('newProd_stock').value);
      const reorder = parseInt(document.getElementById('newProd_reorder').value);

      const res = await fetch('/api/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name, category, emoji, price, stock, reorder })
      });
      const result = await res.json();
      if (result.success) {
        closeNewProductModal();
        fetchFullState();
        showToast(`Added ${name} [${id}]`);
      } else {
        showToast("Error: " + result.message);
      }
    }

    function openRestockModal(id) {
      const sel = document.getElementById('restock_selectItem');
      sel.innerHTML = inventory.map(p => `<option value="${p.id}" ${p.id === id ? 'selected' : ''}>${p.name} (Cur: ${p.stock})</option>`).join('');
      document.getElementById('restockModal').classList.remove('hidden');
    }
    function closeRestockModal() { document.getElementById('restockModal').classList.add('hidden'); }

    async function handleRestockSubmit(e) {
      e.preventDefault();
      const itemId = document.getElementById('restock_selectItem').value;
      const qty = parseInt(document.getElementById('restock_qty').value);
      const note = document.getElementById('restock_note').value.trim() || 'Regular Delivery';

      const res = await fetch('/api/restock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ itemId, qty, note })
      });
      const result = await res.json();
      if (result.success) {
        closeRestockModal();
        fetchFullState();
        showToast(`Restocked +${qty} units`);
      } else {
        showToast("Error: " + result.message);
      }
    }

    function openDbModal() {
      fetch('/api/state').then(r => r.json()).then(data => {
        document.getElementById('cfg_usePg').checked = data.dbStatus?.isPostgres || false;
        document.getElementById('cfg_pgUrl').value = data.dbStatus?.pgUrl || '';
        document.getElementById('dbModal').classList.remove('hidden');
      });
    }
    function closeDbModal() { document.getElementById('dbModal').classList.add('hidden'); }

    async function handleDbSave(e) {
      e.preventDefault();
      const use_postgres = document.getElementById('cfg_usePg').checked;
      const pg_url = document.getElementById('cfg_pgUrl').value;
      const res = await fetch('/api/db-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_postgres, pg_url })
      });
      const result = await res.json();
      closeDbModal();
      fetchFullState();
      showToast(result.message);
    }

    async function triggerDemoLoad() {
      const res = await fetch('/api/demo', { method: 'POST' });
      const result = await res.json();
      fetchFullState();
      showToast("Campus Canteen demo items loaded!");
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.remove('translate-y-20', 'opacity-0');
      setTimeout(() => t.classList.add('translate-y-20', 'opacity-0'), 3200);
    }

    // Initial load
    fetchFullState();
