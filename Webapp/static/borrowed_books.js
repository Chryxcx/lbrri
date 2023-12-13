document.addEventListener('DOMContentLoaded', async function () {

    // Define the search input element
    const searchInput = document.getElementById('search_query');

    searchInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent form submission
        }
    });

    dataArray.forEach(async function (row) {
        const bookId = row['book_id'];
        const qrCodeImg = document.getElementById('qr-code-img-' + bookId);

        // Fetch the QR code image from the server
        const qrCodeUrl = `/qr_codes/${bookId}`;
        const response = await fetch(qrCodeUrl);

        if (response.ok) {
            // Use the fetched QR code image
            qrCodeImg.src = qrCodeUrl;
            qrCodeImg.setAttribute('title', 'Book ID: ' + bookId);
        } else {
            console.error('Error loading QR code image for Book ID:', bookId);
        }
    });
});
