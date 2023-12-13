document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('insert-form');
    const qrImage = document.getElementById('qrImage');
    const downloadBtn = document.getElementById('downloadBtn');

    let responseData;
    let selectedSize = 30;

    function updateQRCodeSize() {
        qrImage.style.width = selectedSize + 'px';
        qrImage.style.height = selectedSize + 'px';
    }

    function changeSize(size) {
        selectedSize = size;
        updateQRCodeSize();
    }

    // Event listeners for size buttons
    document.getElementById('xsmall').addEventListener('click', function () {
        changeSize(57);
    });

    document.getElementById('small').addEventListener('click', function () {
        changeSize(76);
    });

    document.getElementById('medium').addEventListener('click', function () {
        changeSize(94);
    });

    document.getElementById('large').addEventListener('click', function () {
        changeSize(113);
    });

    function showError(message) {
        const flashMessages = document.querySelector('.flash-messages');
        if (flashMessages) {
            flashMessages.innerHTML = '';
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger';
            alert.textContent = message;
            flashMessages.appendChild(alert);
        }
    }

    async function generateQRCodeAndShowModal() {
        try {
            const formData = new FormData(form);
            formData.append('selected_size', selectedSize);

            const response = await fetch('/insert', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                showError('There is something wrong with the server.');
                return;
            }

            try {
                responseData = await response.json();
            } catch (jsonError) {
                console.error('JSON Parsing Error:', jsonError);
                showError('Error parsing server response.');
                return;
            }

            if (!responseData.success) {
                showError('Error generating QR code. Please try again.');
                return;
            }

            // Use the generated QR code image
            qrImage.src = 'data:image/png;base64,' + responseData.qr_image_base64;
            updateQRCodeSize();

            // Show the QR code size buttons and image after generating
            toggleQRCodeVisibility(true);

            clearForm();

        } catch (error) {
            console.error('Error:', error);
            showError('An unexpected error occurred.');
        }
    }
    

    function clearForm() {
        const formInputs = form.querySelectorAll('input[type="text"]');
        formInputs.forEach(input => {
            input.value = ''; // Clear the value of each text input
        });
    }
    // Set up an event listener for form submission
    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        console.log('Form submitted');
        await generateQRCodeAndShowModal();
    });

    // Move the downloadBtn event listener outside of the form submit listener
    downloadBtn.addEventListener('click', function () {
        const downloadedImage = new Image();
        const qrCodeID = responseData.qrCodeID;
        downloadedImage.src = qrImage.src;
        downloadedImage.style.width = selectedSize + 'px';
        downloadedImage.style.height = selectedSize + 'px';

        // Create a temporary canvas to draw the image with the preferred size
        const canvas = document.createElement('canvas');
        canvas.width = selectedSize;
        canvas.height = selectedSize;
        const context = canvas.getContext('2d');
        context.drawImage(downloadedImage, 0, 0, selectedSize, selectedSize);

        // Convert the canvas content to a data URL
        const dataURL = canvas.toDataURL('image/png');

        // Create an anchor element for downloading
        const a = document.createElement('a');
        a.href = dataURL;
        a.download = `${qrCodeID}.png`;
        a.style.display = 'none';

        // Trigger the download by clicking the anchor element
        document.body.appendChild(a);
        a.click();

        // Clean up the anchor element
        document.body.removeChild(a);

        // Hide the QR code elements after clicking download
        toggleQRCodeVisibility(false);
    });

    // Function to toggle QR code size buttons and image visibility
    function toggleQRCodeVisibility(isVisible) {
        const qrBox = document.querySelector('.qrbox');
        qrBox.style.display = isVisible ? 'block' : 'none';
    }

    // Initial setup: Hide the QR code size buttons and image
    toggleQRCodeVisibility(false);
});