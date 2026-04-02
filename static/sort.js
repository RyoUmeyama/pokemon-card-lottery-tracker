let currentSort = { column: 'deadline', direction: 'asc' };

function filterLotteries() {
    const searchText = document.getElementById('searchBox').value.toLowerCase();
    const rows = document.querySelectorAll('#lotteriesTable tbody tr');
    let visibleCount = 0;

    rows.forEach(row => {
        const searchData = row.getAttribute('data-search');
        if (searchData.includes(searchText)) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
}

function sortLotteries() {
    const sortSelect = document.getElementById('sortSelect').value;
    const tbody = document.querySelector('#lotteriesTable tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    rows.sort((a, b) => {
        if (sortSelect === 'deadline') {
            // 期限順（近い順）
            const aDeadline = a.getAttribute('data-deadline') || '';
            const bDeadline = b.getAttribute('data-deadline') || '';
            return aDeadline.localeCompare(bDeadline);
        } else if (sortSelect === 'store') {
            // 店舗名順
            const aStore = a.getAttribute('data-store') || '';
            const bStore = b.getAttribute('data-store') || '';
            return aStore.localeCompare(bStore, 'ja');
        } else if (sortSelect === 'newest') {
            // 新着順（新しい順）
            const aTimestamp = a.getAttribute('data-timestamp') || '0000-00-00';
            const bTimestamp = b.getAttribute('data-timestamp') || '0000-00-00';
            return bTimestamp.localeCompare(aTimestamp);  // 逆順（新しい順）
        }
        return 0;
    });

    // ソート結果を反映
    rows.forEach(row => tbody.appendChild(row));
}

function sortTable(column) {
    const table = document.getElementById('lotteriesTable');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr:not([style*="display: none"])'));

    // ソート方向の切り替え
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }

    // ソート実行
    const columnIndex = {'store': 0, 'product': 1, 'deadline': 2, 'status': 3, 'type': 4}[column];
    rows.sort((a, b) => {
        let aVal = a.children[columnIndex].getAttribute('data-sort-value') || a.children[columnIndex].textContent;
        let bVal = b.children[columnIndex].getAttribute('data-sort-value') || b.children[columnIndex].textContent;

        // 数値ソート試行
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return currentSort.direction === 'asc' ? aNum - bNum : bNum - aNum;
        }

        // 文字列ソート
        if (currentSort.direction === 'asc') {
            return aVal.localeCompare(bVal);
        } else {
            return bVal.localeCompare(aVal);
        }
    });

    // ソート結果を反映
    rows.forEach(row => tbody.appendChild(row));

    // ヘッダのソート状態を更新
    document.querySelectorAll('#lotteriesTable th.sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.getAttribute('data-column') === column) {
            th.classList.add(currentSort.direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
            th.setAttribute('aria-sort', currentSort.direction === 'asc' ? 'ascending' : 'descending');
        } else {
            th.setAttribute('aria-sort', 'none');
        }
    });
}

// ヘッダクリック時にソート実行
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('#lotteriesTable th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            sortTable(th.getAttribute('data-column'));
        });
    });

    // デフォルトで deadline でソート
    sortTable('deadline');
    // ドロップダウンのデフォルト値を設定
    document.getElementById('sortSelect').value = 'deadline';
});
