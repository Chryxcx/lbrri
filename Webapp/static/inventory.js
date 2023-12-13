document.addEventListener('DOMContentLoaded', function () {
    const shelfSelect = document.getElementById('shelf_id');
    const selectedShelfValue = document.getElementById('selected-shelf-value');
    const catSelect = document.getElementById('cate_id');
    const selectedCatalogueValue = document.getElementById('selected-category-value');
    const searchInput = document.getElementById('search_query');
    const inventoryForm = document.getElementById('inventory-form');
    let originalData = [];

    searchInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent form submission
        }
    });

    function fetchInventory() {
        const selectedShelf = shelfSelect.value;
        const selectedCategory = catSelect.value;
        const searchQuery = searchInput.value;

        console.log('Fetching data with parameters:', selectedShelf, selectedCategory, searchQuery);

        fetch(`/inventory?shelf_id=${selectedShelf}&cate_id=${selectedCategory}&search_query=${searchQuery}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Fetched data:', data);
                originalData = data;
                updateTable(data);
            })
            .catch(error => {
                console.error('Fetch error:', error);
            });
    }

    if (inventoryForm) {
        inventoryForm.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent default form submission
            fetchInventory(); // Fetch data when the form is submitted
        });
    }
    searchInput.addEventListener('input', function () {
        const searchQuery = searchInput.value.toLowerCase(); // Convert to lowercase for case-insensitive search
        filterAndDisplayData(searchQuery);
    });

    shelfSelect.addEventListener('change', function () {
        document.getElementById('search_query').value = '';
        const selectedShelf = shelfSelect.value;
        console.log('Selected Shelf:', selectedShelf);
        selectedShelfValue.textContent = selectedShelf;
        const selectedCatalogue = catSelect.value;
        selectedCatalogueValue.textContent = selectedCatalogue;

        if (selectedShelf === 'none') {
            catSelect.disabled = true;
            catSelect.value = 'all';
        } else {
            catSelect.disabled = false;
        }

        // Make a GET request using the fetch API
        fetchInventory();

        // Toggle visibility of Quantity and Availability columns based on the selected shelf
        const hideColumnsShelves = ['shelf01', 'shelf02', 'shelf03', 'shelf04', 'shelf05', 'shelf06', 'shelf07', 'shelf08', 'shelf09', 'shelf10', 'shelf11', 'shelf12', 'shelf13', 'shelf14', 'shelf15'];
        const shouldHideColumns = hideColumnsShelves.includes(selectedShelf);

        const quantityColumnHeader = document.querySelector('#rect4 th:nth-child(7)');
        const quantityColumnCells = document.querySelectorAll('#rect4 td:nth-child(7)');
        const availabilityColumnHeader = document.querySelector('#rect4 th:nth-child(8)');
        const availabilityColumnCells = document.querySelectorAll('#rect4 td:nth-child(8)');

        if (shouldHideColumns) {
            quantityColumnHeader.style.display = 'none';
            availabilityColumnHeader.style.display = 'none';
            quantityColumnCells.forEach(cell => cell.style.display = 'none');
            availabilityColumnCells.forEach(cell => cell.style.display = 'none');
        } else {
            quantityColumnHeader.style.display = '';
            availabilityColumnHeader.style.display = '';
            quantityColumnCells.forEach(cell => cell.style.display = '');
            availabilityColumnCells.forEach(cell => cell.style.display = '');
        }
    });

    catSelect.addEventListener('change', function () {
        document.getElementById('search_query').value = '';
        const selectedCatalogue = catSelect.value;
        selectedCatalogueValue.textContent = selectedCatalogue;

        // Perform a fetch request based on the selected shelf and category
        fetchInventory();
    });

    function filterAndDisplayData(searchQuery) {
        const filteredData = originalData.filter(item => {
            return item.title.toLowerCase().includes(searchQuery) || item.publisher.toLowerCase().includes(searchQuery);
        });

        updateTable(filteredData);
    }

    // Function to update the table with new data
    function updateTable(data) {
        const booksTableBody = document.getElementById('table-body');
        booksTableBody.innerHTML = '';

        data.forEach(row => {
            const newRow = booksTableBody.insertRow();
            const qrCell = newRow.insertCell();
            const qrImage = new Image();

            // Set the QR code image source based on the book_data.book_id
            qrImage.src = `/qr_codes/${row.book_id}`;
            qrImage.alt = 'QR Code';
            qrImage.classList.add('qr-code-size');
            qrImage.id = `qr-code-img-${row.book_id}`;
            qrCell.appendChild(qrImage);

            // Populate other table cells
            if ('quantity' in row && 'availability' in row) {
                newRow.insertCell().textContent = row.category;
                newRow.insertCell().textContent = row.isbn;
                newRow.insertCell().textContent = row.title;
                newRow.insertCell().textContent = row.publisher;
                newRow.insertCell().textContent = row.year_published;
                newRow.insertCell().textContent = row.quantity;
                newRow.insertCell().textContent = row.availability;
            } else {
                newRow.insertCell().textContent = row.category;
                newRow.insertCell().textContent = row.isbn;
                newRow.insertCell().textContent = row.title;
                newRow.insertCell().textContent = row.publisher;
                newRow.insertCell().textContent = row.year_published;
            }
        });
    }
});
