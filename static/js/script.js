document.addEventListener('DOMContentLoaded', function() {
    const sliderContainer = document.querySelector('.slider-container');
    const slides = document.querySelectorAll('.slide');
    let currentSlide = 0;
    
    // Carousel interval (3 seconds)
    const INTERVAL = 3000;
    
    function nextSlide() {
        currentSlide = (currentSlide + 1) % slides.length;
        updateSlider();
    }
    
    function updateSlider() {
        sliderContainer.style.transform = `translateX(-${currentSlide * 100}%)`;
    }
    
    // Auto carousel
    setInterval(nextSlide, INTERVAL);
    
    // Initialize display
    updateSlider();
}); 