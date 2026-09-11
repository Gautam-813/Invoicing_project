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

    // --- Upload Logic ---
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadPreview = document.getElementById('uploadPreview');
    const previewThumb = document.getElementById('previewThumb');
    const previewName = document.getElementById('previewName');
    const previewSize = document.getElementById('previewSize');
    const removeFile = document.getElementById('removeFile');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadStatus = document.getElementById('uploadStatus');
    const chatIdInput = document.getElementById('chatIdInput');
    const vendorInput = document.getElementById('vendorInput');
    const amountInput = document.getElementById('amountInput');

    let selectedFile = null;

    // Click to browse
    uploadArea.addEventListener('click', () => fileInput.click());

    // Drag & drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFileSelect(file);
    });

    // File input change
    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) handleFileSelect(fileInput.files[0]);
    });

    function handleFileSelect(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
        if (!validTypes.includes(file.type)) {
            uploadStatus.textContent = 'Invalid file type. Use JPG, PNG, or PDF.';
            uploadStatus.className = 'upload-status error';
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            uploadStatus.textContent = 'File too large. Maximum 10MB.';
            uploadStatus.className = 'upload-status error';
            return;
        }

        selectedFile = file;
        uploadStatus.textContent = '';
        uploadStatus.className = 'upload-status';

        // Show preview
        uploadArea.style.display = 'none';
        uploadPreview.style.display = 'flex';
        previewName.textContent = file.name;
        previewSize.textContent = (file.size / 1024).toFixed(1) + ' KB';

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => { previewThumb.src = e.target.result; };
            reader.readAsDataURL(file);
        } else {
            previewThumb.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%239aa0a6"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2l5 5h-5V4zM6 20V4h6v7h7v9H6z"/></svg>';
        }

        uploadBtn.disabled = false;
    }

    // Remove file
    removeFile.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        uploadArea.style.display = '';
        uploadPreview.style.display = 'none';
        uploadBtn.disabled = true;
        uploadStatus.textContent = '';
    });

    // Upload to Telegram
    uploadBtn.addEventListener('click', async () => {
        const chatId = chatIdInput.value.trim();
        if (!chatId) {
            uploadStatus.textContent = 'Please enter your Telegram User ID.';
            uploadStatus.className = 'upload-status error';
            return;
        }
        if (!selectedFile) {
            uploadStatus.textContent = 'Please select a file.';
            uploadStatus.className = 'upload-status error';
            return;
        }

        uploadBtn.disabled = true;
        uploadStatus.textContent = 'Uploading to Telegram...';
        uploadStatus.className = 'upload-status loading';

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('chat_id', chatId);
        formData.append('vendor', vendorInput.value.trim() || 'Pending Extraction');
        formData.append('amount', parseFloat(amountInput.value) || 0.0);

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.success) {
                uploadStatus.textContent = 'Invoice uploaded to Telegram successfully!';
                uploadStatus.className = 'upload-status success';
                selectedFile = null;
                fileInput.value = '';
                uploadArea.style.display = '';
                uploadPreview.style.display = 'none';
                vendorInput.value = '';
                amountInput.value = '';
                // Refresh table
                fetchInvoices();
            } else {
                uploadStatus.textContent = data.error || 'Upload failed.';
                uploadStatus.className = 'upload-status error';
                uploadBtn.disabled = false;
            }
        } catch (err) {
            uploadStatus.textContent = 'Network error. Try again.';
            uploadStatus.className = 'upload-status error';
            uploadBtn.disabled = false;
        }
    });
});
