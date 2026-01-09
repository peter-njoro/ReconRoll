function toggleView(containerId, viewType) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const images = container.querySelectorAll('img');
    images.forEach(img => {
        if (img.dataset.view === viewType) {
            img.classList.remove('hide-view');
            img.classList.add('show-view');
        } else {
            img.classList.remove('show-view');
            img.classList.add('hide-view');
        }
    });
}