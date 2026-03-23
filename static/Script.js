// Apple-style interactions for Tampering Detector
document.addEventListener('DOMContentLoaded', function() {
    console.log('Apple-style Tampering Detector loaded');
    
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    let lastScrollY = window.scrollY;
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        lastScrollY = window.scrollY;
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^=\"#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // File upload enhancements
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.getElementById('imageInput');
    const submitBtn = document.getElementById('submitBtn');
    const form = document.getElementById('uploadForm');
    
    if (uploadArea && fileInput) {
        // Click to trigger file input
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag & drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            uploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
            uploadArea.classList.remove('dragover');
        }
        
        // Handle dropped files
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            fileInput.files = files;
            
            const fileName = files[0] ? files[0].name : '';
            if (fileName) {
                uploadArea.querySelector('.upload-text').textContent = `Selected: ${fileName}`;
            }
        }
        
        // File input change
        fileInput.addEventListener('change', function() {
            if (this.files.length) {
                uploadArea.querySelector('.upload-text').textContent = `Selected: ${this.files[0].name}`;
                submitBtn.disabled = false;
            } else {
                uploadArea.querySelector('.upload-text').textContent = 'Upload Your Image';
                submitBtn.disabled = true;
            }
        });
    }
    
    // Form submission loading
    if (form && submitBtn) {
        form.addEventListener('submit', function() {
            submitBtn.innerHTML = '<div class="loading"></div> Analyzing...';
            submitBtn.disabled = true;
        });
    }
    
    // Fade in animations on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.fade-in, .feature-card, .image-card').forEach(el => {
        observer.observe(el);
    });
    
    // Image card zoom hover
    document.querySelectorAll('.image-card').forEach(card => {
        card.addEventListener('click', function() {
            const img = this.querySelector('img');
            if (img) {
                // Open full size in new tab (simplified lightbox)
                window.open(img.src, '_blank');
            }
        });
    });
    
    // Navbar mobile toggle (basic)
    const navToggle = document.createElement('button');
    navToggle.innerHTML = '☰';
    navToggle.style.cssText = `
        display: none;
        background: none;
        border: none;
        color: var(--text-primary);
        font-size: 24px;
        cursor: pointer;
        padding: 8px;
        @media (max-width: 768px) { display: block; }
    `;
    navbar.querySelector('.navbar-content').appendChild(navToggle);
    
    // Mobile menu toggle (placeholder)
    navToggle.addEventListener('click', () => {
        const menu = document.querySelector('.nav-menu');
        menu.style.display = menu.style.display === 'flex' ? 'none' : 'flex';
    });
});

