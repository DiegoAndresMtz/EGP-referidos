
    function toggleLeadDetails(id) {
        const row = document.getElementById('details-' + id);
        if (row.style.display === 'none') {
            row.style.display = 'table-row';
            row.style.animation = 'slideDown 0.3s ease';
        } else {
            row.style.display = 'none';
        }
    }
