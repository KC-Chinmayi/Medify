// Load initial all medicines by sending empty query
window.onload = () => {
    searchMedicines("");
    startCarousel();
};

// Carousel Logic --sliding thing in the webpage
let slideIndex = 0;
let slideInterval;
function startCarousel() {
    slideInterval = setInterval(() => { changeSlide(1); }, 5000);
}

function changeSlide(n) {
    showSlide(slideIndex += n);
}
function currentSlide(n) {
    showSlide(slideIndex = n);
    clearInterval(slideInterval);
    startCarousel();
}
function showSlide(n) {
    const slides = document.getElementsByClassName("carousel-slide");
    const dots = document.getElementsByClassName("dot");
    if (!slides.length) return;
    if (n >= slides.length) slideIndex = 0;
    if (n < 0) slideIndex = slides.length - 1;
    for (let i = 0; i < slides.length; i++) slides[i].classList.remove("active");
    for (let i = 0; i < dots.length; i++) dots[i].classList.remove("active");
    slides[slideIndex].classList.add("active");
    dots[slideIndex].classList.add("active");
}

function displayMedicines(medicines, title="Search Results") {
    document.getElementById("resultsTitle").innerText = title;
    const grid = document.getElementById("resultsGrid");

    if (medicines && medicines.length > 0) {
        let html = "";
        medicines.forEach(med => {
            html += `
                <div class="card">
                    <div class="card-img">
                        <img src="${med.image}" alt="${med.name}" style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 4px;">
                    </div>
                    <div>
                        <div class="card-title">${med.name}</div>
                        <div class="card-desc">${med.description}</div>
                        <div class="card-price">₹${med.price}</div>
                    </div>
                    <button class="add-to-cart" data-id="${med.id}" data-name="${med.name}" data-price="${med.price}">ADD TO CART</button>
                </div>
            `;
        });
        grid.innerHTML = html;

        grid.querySelectorAll(".add-to-cart").forEach(button => {
            button.addEventListener("click", () => {
                openModal(Number(button.dataset.id), button.dataset.name, Number(button.dataset.price));
            });
        });
    } else {
        grid.innerHTML = "<p>No medicines found for your query.</p>";
    }
}

function searchMedicines(forceQuery = null) {
    const query = forceQuery !== null ? forceQuery : document.getElementById("searchInput").value;
    const grid = document.getElementById("resultsGrid");
    grid.innerHTML = "<p>Searching...</p>";
    document.getElementById("aiBanner").style.display = "none";

    fetch(`/medicines/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => displayMedicines(data.medicines, query ? `Results for "${query}"` : "All Medicines"))
        .catch(e => { grid.innerHTML = "<p>Error loading catalog.</p>"; });
}

function startVoiceSearch() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { alert("Voice search not supported in this browser."); return; }

    const recognition = new SpeechRecognition();
    const voiceBtn = document.getElementById('voiceBtn');
    const searchInput = document.getElementById("searchInput");

    recognition.onstart = function() {
        voiceBtn.classList.add("recording");
        searchInput.placeholder = "Listening to your symptoms...";
        searchInput.value = "";
    };

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        searchInput.value = transcript;
        callAIAssistant(transcript);
    };

    recognition.onend = function() {
        voiceBtn.classList.remove("recording");
        searchInput.placeholder = "Search for medicines or describe your symptoms...";
    };

    recognition.start();
}

function callAIAssistant(symptoms) {
    const grid = document.getElementById("resultsGrid");
    grid.innerHTML = "<p>Analyzing your symptoms...</p>";

    fetch(`/ai/recommend/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptoms: symptoms })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const banner = document.getElementById("aiBanner");
            banner.style.display = "block";
            document.getElementById("aiAdvice").innerText = data.advice;
            document.getElementById("aiDisclaimer").innerText = `⚠️ ${data.disclaimer}`;

            displayMedicines(data.medicines, "Recommended Medicines");
        } else {
            grid.innerHTML = `<p style="color: red;">${data.error}</p>`;
        }
    })
    .catch(e => { grid.innerHTML = "<p>Service offline.</p>"; });
}

// Checkout & AI Validation Flow
let currentPrice = 0;
let isVerified = false;

function openModal(id, name, price) {
    document.getElementById("checkoutModal").style.display = "flex";
    document.getElementById("checkoutMedicineId").value = id;
    document.getElementById("checkoutMedicineName").value = name;
    currentPrice = price;
    isVerified = false;
    document.getElementById("aiCheckoutAdvice").style.display = "none";
    document.getElementById("proceedBtn").innerText = "Verify Profile with AI";
}

function closeModal() {
    document.getElementById("checkoutModal").style.display = "none";
}

function verifyAndCheckout() {
    const btn = document.getElementById("proceedBtn");
    const name = document.getElementById("patientName").value;
    const diabetes = document.getElementById("hasDiabetes").checked;
    const thyroid = document.getElementById("hasThyroid").checked;
    const other = document.getElementById("otherConditions").value;
    const medName = document.getElementById("checkoutMedicineName").value;

    if (!name) { alert("Please enter Patient Name"); return; }

    if (!isVerified) {
        // Step 1: Verify with AI
        btn.innerText = "Verifying...";
        btn.disabled = true;

        // Simulating the AI verification response.
        setTimeout(() => {
            const adviceBox = document.getElementById("aiCheckoutAdvice");
            adviceBox.style.display = "block";

            let advice = `<strong>Medical Note:</strong> For ${medName}, please take 1 dose after meals. `;
            if (diabetes && medName.includes("Syrup")) {
                advice += `<br><span style="color:red;">⚠️ WARNING: Since you have Diabetes, please ensure this syrup is sugar-free.</span>`;
            } else if (diabetes) {
                advice += `Safe for diabetic patients if taken as prescribed.`;
            } else if (thyroid) {
                advice += `Does not interfere with thyroid medication. Take normally.`;
            } else {
                advice += `Standard dosage applies. No contraindications found with your profile.`;
            }

            adviceBox.innerHTML = advice;
            btn.innerText = `Pay ₹${currentPrice} securely`;
            btn.disabled = false;
            isVerified = true;
        }, 1500);

    } else {
        // Step 2: Razorpay Fake Payment
        const options = {
            "key": "rzp_test_Shn78qatVKaTIB",
            "amount": currentPrice * 100,
            "currency": "INR",
            "name": "Medify",
            "description": "Medicine Purchase",
            "handler": function (response){
                // Save Order to Backend MySQL
                fetch('/orders/create/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        medicine_id: document.getElementById("checkoutMedicineId").value,
                        patient_name: name,
                        amount: currentPrice,
                        payment_id: response.razorpay_payment_id
                    })
                }).then(() => {
                    alert(`Payment Successful & Order Recorded! Razorpay Payment ID: ${response.razorpay_payment_id}`);
                    let count = parseInt(document.getElementById("cartCount").innerText) + 1;
                    document.getElementById("cartCount").innerText = count;
                    closeModal();
                });
            },
            "prefill": { "name": name, "email": "user@medify.com" },
            "theme": { "color": "#d32f2f" }
        };
        const rzp1 = new Razorpay(options);
        rzp1.on('payment.failed', function (response){
            alert("Payment Failed! Reason: " + response.error.description);
        });
        rzp1.open();
    }
}
