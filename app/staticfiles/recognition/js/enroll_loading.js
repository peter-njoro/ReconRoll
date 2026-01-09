document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector('form');
    if (!form) return;

    // Create loading overlay with progress bar
    const loader = document.createElement('div');
    loader.id = 'enroll-loading-overlay';
    loader.style.display = 'none';
    loader.style.position = 'fixed';
    loader.style.top = 0;
    loader.style.left = 0;
    loader.style.width = '100vw';
    loader.style.height = '100vh';
    loader.style.background = 'rgba(255, 255, 255, 0.8)';
    loader.style.zIndex = 9999;
    loader.style.justifyContent = 'center';
    loader.style.alignItems = 'center';
    loader.innerHTML = `
        <div style="text-align:center; min-width:300px;">
            <div style="margin-bottom:1rem;font-size:1.2rem;">Processing images, just chill😎...</div>
            <div class="progress" style="height: 2rem;">
                <div id="enroll-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated bg-primary"
                    role="progressbar" style="width: 0%; font-size:1.1rem;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                    0%
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(loader);

    let pollInterval = null;
    let fakeProgress = 0;
    let fakeMax = Math.floor(Math.random() * 30) + 60; // Random stop between 60-90%

    form.addEventListener('submit', function () {
        loader.style.display = 'flex';
        fakeProgress = 0;
        fakeMax = Math.floor(Math.random() * 30) + 60;

        // Start fake progress
        const progressBar = document.getElementById('enroll-progress-bar');
        let fakeInterval = setInterval(function () {
            if (fakeProgress < fakeMax) {
                fakeProgress += Math.floor(Math.random() * 3) + 1; // Increment by 1-3%
                if (fakeProgress > fakeMax) fakeProgress = fakeMax;
                progressBar.style.width = fakeProgress + '%';
                progressBar.innerText = fakeProgress + '%';
                progressBar.setAttribute('aria-valuenow', fakeProgress);
            }
        }, 300);

        // Start polling backend for real completion
        pollInterval = setInterval(function () {
            fetch('/enroll/progress/')
                .then(response => response.json())
                .then(data => {
                    if (data.progress >= 100) {
                        clearInterval(pollInterval);
                        clearInterval(fakeInterval);
                        progressBar.style.width = '100%';
                        progressBar.innerText = '100%';
                        progressBar.setAttribute('aria-valuenow', 100);
                    }
                });
        }, 500);
    });
});