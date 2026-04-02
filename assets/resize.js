document.addEventListener('mousedown', function (e) {
    if (e.target && e.target.id === 'drag-handle') {
        let offcanvas = e.target.closest('.offcanvas');
        if (!offcanvas) return;

        let startX = e.clientX;
        let startWidth = parseFloat(window.getComputedStyle(offcanvas).width);

        document.body.style.userSelect = 'none';

        function onMouseMove(ev) {
            let dx = ev.clientX - startX;
            let newWidth = startWidth - dx;
            if (newWidth < 300) newWidth = 300;
            if (newWidth > window.innerWidth * 0.95) newWidth = window.innerWidth * 0.95;
            offcanvas.style.setProperty('width', newWidth + 'px', 'important');
        }

        function onMouseUp() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.body.style.userSelect = '';
        }

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }
});
