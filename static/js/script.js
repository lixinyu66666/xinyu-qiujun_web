document.addEventListener('DOMContentLoaded', function() {
    // Carousel elements
    const sliderContainer = document.querySelector('.slider-container');
    const slides = document.querySelectorAll('.slide');
    const prevBtn = document.querySelector('.prev-btn');
    const nextBtn = document.querySelector('.next-btn');
    let currentSlide = 0;
    let autoPlayInterval;
    
    // Fullscreen elements
    const fullscreenOverlay = document.querySelector('.fullscreen-overlay');
    const fullscreenImage = document.querySelector('.fullscreen-content img');
    const closeFullscreenBtn = document.querySelector('.close-fullscreen');
    const imgContainers = document.querySelectorAll('.img-container');
    
    // Background color animation
    const backgroundOverlay = document.querySelector('.background-overlay');
    let colorIndex = 0;
    
    // Carousel interval (7 seconds)
    const INTERVAL = 7000;
    
    // Navigation functions
    function goToNextSlide() {
        currentSlide = (currentSlide + 1) % slides.length;
        updateSlider();
    }
    
    function goToPrevSlide() {
        currentSlide = (currentSlide - 1 + slides.length) % slides.length;
        updateSlider();
    }
    
    function updateSlider() {
        sliderContainer.style.transform = `translateX(-${currentSlide * 100}%)`;
        
        // Update slide indicator
        const currentSlideIndicator = document.querySelector('.current-slide');
        if (currentSlideIndicator) {
            currentSlideIndicator.textContent = currentSlide + 1;
        }
    }
    
    // Add click event listeners for manual navigation
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            // Stop auto play temporarily
            clearInterval(autoPlayInterval);
            goToNextSlide();
            // Resume auto play after manual navigation
            startAutoPlay();
        });
    }
    
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            // Stop auto play temporarily
            clearInterval(autoPlayInterval);
            goToPrevSlide();
            // Resume auto play after manual navigation
            startAutoPlay();
        });
    }
    
    // Function to start auto play
    function startAutoPlay() {
        // Clear any existing interval first
        clearInterval(autoPlayInterval);
        autoPlayInterval = setInterval(goToNextSlide, INTERVAL);
    }
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft') {
            clearInterval(autoPlayInterval);
            goToPrevSlide();
            startAutoPlay();
        } else if (e.key === 'ArrowRight') {
            clearInterval(autoPlayInterval);
            goToNextSlide();
            startAutoPlay();
        } else if (e.key === 'Escape' && fullscreenOverlay.style.display === 'flex') {
            closeFullscreen();
        }
    });
    
    // Fullscreen mode functions
    function openFullscreen(imageSrc) {
        fullscreenImage.src = imageSrc;
        fullscreenOverlay.style.display = 'flex';
        setTimeout(() => {
            fullscreenOverlay.style.opacity = 1;
        }, 10);
        
        // Pause auto play when in fullscreen
        clearInterval(autoPlayInterval);
    }
    
    function closeFullscreen() {
        fullscreenOverlay.style.opacity = 0;
        setTimeout(() => {
            fullscreenOverlay.style.display = 'none';
        }, 300);
        
        // Resume auto play after closing fullscreen
        startAutoPlay();
    }
    
    // Set up fullscreen viewers
    imgContainers.forEach(container => {
        container.addEventListener('click', function() {
            const imageSrc = this.getAttribute('data-image');
            openFullscreen(imageSrc);
        });
    });
    
    closeFullscreenBtn.addEventListener('click', closeFullscreen);
    
    fullscreenOverlay.addEventListener('click', function(e) {
        if (e.target === fullscreenOverlay) {
            closeFullscreen();
        }
    });
    
    // Touch swipe support for mobile
    let touchStartX = 0;
    let touchEndX = 0;
    
    sliderContainer.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, false);
    
    sliderContainer.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, false);
    
    function handleSwipe() {
        clearInterval(autoPlayInterval);
        if (touchEndX < touchStartX - 50) {
            goToNextSlide();
        } else if (touchEndX > touchStartX + 50) {
            goToPrevSlide();
        }
        startAutoPlay();
    }
    
    // Initialize carousel
    startAutoPlay();
    updateSlider();
}); 