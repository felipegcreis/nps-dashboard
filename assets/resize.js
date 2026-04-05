function startResize(startX, offcanvas) {
    let startWidth = parseFloat(window.getComputedStyle(offcanvas).width);
    document.body.style.userSelect = 'none';

    function onMove(clientX) {
        let dx = clientX - startX;
        let newWidth = startWidth - dx;
        if (newWidth < 280) newWidth = 280;
        if (newWidth > window.innerWidth * 0.95) newWidth = window.innerWidth * 0.95;
        offcanvas.style.setProperty('width', newWidth + 'px', 'important');
    }

    function onMouseMove(ev) { onMove(ev.clientX); }
    function onTouchMove(ev) { onMove(ev.touches[0].clientX); }

    function cleanup() {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', cleanup);
        document.removeEventListener('touchmove', onTouchMove);
        document.removeEventListener('touchend', cleanup);
        document.body.style.userSelect = '';
    }

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', cleanup);
    document.addEventListener('touchmove', onTouchMove, { passive: true });
    document.addEventListener('touchend', cleanup);
}

document.addEventListener('mousedown', function (e) {
    if (e.target && e.target.id === 'drag-handle') {
        let offcanvas = e.target.closest('.offcanvas');
        if (offcanvas) startResize(e.clientX, offcanvas);
    }
});

document.addEventListener('touchstart', function (e) {
    if (e.target && e.target.id === 'drag-handle') {
        let offcanvas = e.target.closest('.offcanvas');
        if (offcanvas) startResize(e.touches[0].clientX, offcanvas);
    }
}, { passive: true });
