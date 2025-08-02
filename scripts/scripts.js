function fetchProgress() {
  fetch("{% url 'recognition:recognition_progress_partial' session.id %}")
    .then(response => response.json())
    .then(data => {
      document.getElementById('present-count').innerText = data.present_count;
      document.getElementById('total-expected').innerText = data.total_expected;
      document.getElementById('unknown-count').innerText = data.unknown_count;
    });
}

setInterval(fetchProgress, 3000);
fetchProgress(); // initial load
