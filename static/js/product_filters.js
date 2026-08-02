document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('filter-form');
    const gridWrapper = document.querySelector('main');
    let debounceTimer = null;

    function fetchProducts(params, pushUrl = true) {
        const url = '?' + params.toString();
        fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(res => res.json())
            .then(data => {
                gridWrapper.innerHTML = data.html;
                if (pushUrl) {
                    history.pushState(null, '', url);
                }
                attachPaginationHandlers();
            });
    }

    function getFormParams() {
        return new URLSearchParams(new FormData(form));
    }

    function attachPaginationHandlers() {
        document.querySelectorAll('#product-pagination .page-link').forEach(link => {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                const pageUrl = new URL(this.href);
                const params = getFormParams();
                params.set('page', pageUrl.searchParams.get('page'));
                fetchProducts(params);
            });
        });
    }

    
    const searchInput = form.querySelector('input[name="q"]');
    searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchProducts(getFormParams());
        }, 400);
    });

    form.querySelectorAll('select, input[type="number"], input[type="checkbox"]').forEach(el => {
        el.addEventListener('change', function () {
            fetchProducts(getFormParams());
        });
    });

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        fetchProducts(getFormParams());
    });

    attachPaginationHandlers();
});