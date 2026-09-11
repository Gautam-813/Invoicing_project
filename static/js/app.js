document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const applyBtn = document.getElementById('applyFilters');
    const tableBody = document.getElementById('invoiceTableBody');
    const modal = document.getElementById('previewModal');
    const closeModal = document.getElementById('closeModal');
    const modalBody = document.getElementById('modalBody');
    const modalTitle = document.getElementById('modalTitle');
    const modalMeta = document.getElementById('modalMeta');

    let allInvoices = [];

    // Filter mode radio buttons
    const filterRadios = document.querySelectorAll('input[name="filterMode"]');
    const dateFilters = document.getElementById('dateFilters');
    const specificDateGroup = document.getElementById('specificDateGroup');
    const startDateGroup = document.getElementById('startDateGroup');
    const endDateGroup = document.getElementById('endDateGroup');

    filterRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            const val = radio.value;
            dateFilters.style.display = val === 'all' ? 'none' : 'flex';
            specificDateGroup.style.display = val === 'specific' ? 'block' : 'none';
            startDateGroup.style.display = val === 'range' ? 'block' : 'none';
            endDateGroup.style.display = val === 'range' ? 'block' : 'none';
        });
    });

    // Fetch invoices
    async function fetchInvoices() {
        const mode = document.querySelector('input[name="filterMode"]:checked').value;
        const params = new URLSearchParams();

        if (mode === 'specific') {
            const d = document.getElementById('specificDate').value;
            if (d) {
                params.set('start_date', d);
                params.set('end_date', d);
            }
        } else if (mode === 'range') {
            const s = document.getElementById('startDate').value;
            const e = document.getElementById('endDate').value;
            if (s) params.set('start_date', s);
            if (e) params.set('end_date', e);
        }

        const search = searchInput.value.trim();
        if (search) params.set('search', search);

        try {
            const res = await fetch(`/api/invoices?${params.toString()}`);
            allInvoices = await res.json();
            renderTable(allInvoices);
            updateStats(allInvoices);
        } catch (err) {
            tableBody.innerHTML = '<tr><td colspan="7" class="empty-state">Failed to load invoices.</td></tr>';
        }
    }

    function renderTable(invoices) {
        if (!invoices.length) {
            tableBody.innerHTML = '<tr><td colspan="7" class="empty-state">No invoices found.</td></tr>';
            return;
        }

        tableBody.innerHTML = invoices.map(inv => `
            <tr>
                <td>${inv.id}</td>
                <td>${inv.user_id}</td>
                <td><span class="type-badge ${inv.file_type}">${inv.file_type}</span></td>
                <td>${inv.vendor}</td>
                <td class="amount">$${inv.amount.toFixed(2)}</td>
                <td>${inv.upload_date || 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="previewInvoice(${inv.id})">Preview</button>
                </td>
            </tr>
        `).join('');
    }

    function updateStats(invoices) {
        document.getElementById('totalCount').textContent = invoices.length;

        const now = new Date();
        const thisMonth = invoices.filter(inv => {
            if (!inv.upload_date) return false;
            const d = new Date(inv.upload_date);
            return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
        });
        document.getElementById('monthCount').textContent = thisMonth.length;

        const total = invoices.reduce((sum, inv) => sum + inv.amount, 0);
        document.getElementById('totalValue').textContent = `$${total.toFixed(2)}`;
    }

    // Preview modal
    window.previewInvoice = async function(id) {
        const inv = allInvoices.find(i => i.id === id);
        if (!inv) return;

        modal.classList.add('active');
        modalTitle.textContent = `Invoice #${inv.id}`;
        modalMeta.textContent = `${inv.vendor} — $${inv.amount.toFixed(2)} — ${inv.upload_date || ''}`;
        modalBody.innerHTML = '<div class="loading-spinner">Loading file from Telegram...</div>';

        try {
            const res = await fetch(`/api/invoices/${id}/file-url`);
            const data = await res.json();

            if (data.url) {
                if (inv.file_type === 'photo') {
                    modalBody.innerHTML = `<img src="${data.url}" alt="Invoice #${id}" onclick="this.classList.toggle('zoomed')" />`;
                } else if (inv.file_type === 'document') {
                    modalBody.innerHTML = `
                        <div style="text-align: center; width: 100%;">
                            <a href="${data.url}" target="_blank" class="download-link">Download PDF</a>
                            <div style="margin-top: 20px;">
                                <iframe src="${data.url}" class="pdf-container" title="PDF Preview"></iframe>
                            </div>
                        </div>
                    `;
                } else {
                    modalBody.innerHTML = `<a href="${data.url}" target="_blank" class="download-link">Download File</a>`;
                }
            } else {
                modalBody.innerHTML = '<div class="loading-spinner">Failed to load file from Telegram.</div>';
            }
        } catch (err) {
            modalBody.innerHTML = '<div class="loading-spinner">Error fetching file.</div>';
        }
    };

    // Close modal
    closeModal.addEventListener('click', () => {
        modal.classList.remove('active');
        modalBody.innerHTML = '';
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
            modalBody.innerHTML = '';
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            modal.classList.remove('active');
            modalBody.innerHTML = '';
        }
    });

    // Apply filters
    applyBtn.addEventListener('click', fetchInvoices);

    // Search on enter
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') fetchInvoices();
    });

    // Initial load
    fetchInvoices();
});
