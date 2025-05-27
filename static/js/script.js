document.addEventListener('DOMContentLoaded', function() {
    const sliderContainer = document.querySelector('.slider-container');
    const slides = document.querySelectorAll('.slide');
    let currentSlide = 0;
    
    // 设置轮播间隔（3秒）
    const INTERVAL = 3000;
    
    function nextSlide() {
        currentSlide = (currentSlide + 1) % slides.length;
        updateSlider();
    }
    
    function updateSlider() {
        sliderContainer.style.transform = `translateX(-${currentSlide * 100}%)`;
    }
    
    // 自动轮播
    setInterval(nextSlide, INTERVAL);
    
    // 初始化显示
    updateSlider();
}); 