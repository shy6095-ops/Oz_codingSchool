/**
 * 챌린저 57 - Javascript 3일차
 * fetch / async-await 로 Binance 공개 API에서 24시간 시세를 받아 표로 보여준다.
 * - 전체보기 / 관심목록 탭
 * - 심볼 검색, 정렬(심볼·상승률·하락률·거래대금)
 * - 관심목록은 localStorage 에 저장해 새로고침 후에도 유지
 * - 30초마다 자동 갱신
 */

const API_URL = "https://api4.binance.com/api/v3/ticker/24hr";
const FAVORITES_KEY = "hans-crypto-favorites";
const REFRESH_INTERVAL_MS = 30000;

const els = {
    status: document.getElementById("status"),
    table: document.getElementById("cryptoTable"),
    body: document.getElementById("cryptoBody"),
    search: document.getElementById("searchBox"),
    sort: document.getElementById("sortSelect"),
    tabs: document.querySelectorAll(".tab-btn"),
    favCount: document.getElementById("favCount"),
    updatedAt: document.getElementById("updatedAt"),
    refresh: document.getElementById("refreshBtn"),
};

let allCoins = [];
let currentTab = "all";
let favorites = loadFavorites();

/* ---------- 관심목록 (localStorage) ---------- */

function loadFavorites() {
    try {
        const saved = JSON.parse(localStorage.getItem(FAVORITES_KEY));
        return Array.isArray(saved) ? saved : [];
    } catch {
        return [];
    }
}

function saveFavorites() {
    try {
        localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
    } catch {
        console.warn("관심목록을 저장할 수 없습니다.");
    }
}

function toggleFavorite(symbol) {
    const index = favorites.indexOf(symbol);

    if (index === -1) {
        favorites.push(symbol);
    } else {
        favorites.splice(index, 1);
    }

    saveFavorites();
    render();
}

/* ---------- 데이터 가져오기 ---------- */

async function fetchCoins() {
    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error(`서버 응답 오류 (${response.status})`);
        }

        const data = await response.json();

        allCoins = data
            .filter((coin) => coin.symbol.endsWith("USDT") && Number(coin.lastPrice) > 0)
            .map((coin) => ({
                symbol: coin.symbol,
                price: Number(coin.lastPrice),
                changePercent: Number(coin.priceChangePercent),
                high: Number(coin.highPrice),
                low: Number(coin.lowPrice),
                quoteVolume: Number(coin.quoteVolume),
            }));

        els.status.classList.add("hidden");
        els.table.classList.remove("hidden");
        els.updatedAt.textContent = `마지막 갱신 ${new Date().toLocaleTimeString("ko-KR")}`;
        render();
    } catch (error) {
        els.status.classList.remove("hidden");
        els.status.textContent = `데이터를 불러오지 못했습니다: ${error.message}`;
        els.updatedAt.textContent = "갱신 실패";
    }
}

/* ---------- 필터 / 정렬 ---------- */

const SORTERS = {
    symbol: (a, b) => a.symbol.localeCompare(b.symbol),
    "change-desc": (a, b) => b.changePercent - a.changePercent,
    "change-asc": (a, b) => a.changePercent - b.changePercent,
    volume: (a, b) => b.quoteVolume - a.quoteVolume,
};

function getVisibleCoins() {
    const keyword = els.search.value.trim().toUpperCase();

    let visible = allCoins.filter((coin) => coin.symbol.includes(keyword));

    if (currentTab === "favorites") {
        visible = visible.filter((coin) => favorites.includes(coin.symbol));
    }

    return visible.sort(SORTERS[els.sort.value]);
}

/* ---------- 출력 ---------- */

function formatPrice(value) {
    const digits = value >= 1 ? 2 : 8;
    return value.toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

function formatVolume(value) {
    if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
    return value.toFixed(2);
}

function render() {
    els.favCount.textContent = String(favorites.length);

    const coins = getVisibleCoins();
    els.body.innerHTML = "";

    if (coins.length === 0) {
        const message = currentTab === "favorites"
            ? "관심목록이 비어 있습니다. ☆ 를 눌러 추가해보세요."
            : "검색 결과가 없습니다.";
        els.body.innerHTML = `<tr><td colspan="7" class="empty">${message}</td></tr>`;
        return;
    }

    const rows = coins.map((coin) => {
        const isUp = coin.changePercent >= 0;
        const sign = isUp ? "+" : "";
        const isFavorite = favorites.includes(coin.symbol);

        return `
            <tr>
                <td>
                    <button class="fav-btn" data-symbol="${coin.symbol}" aria-label="관심 등록">
                        ${isFavorite ? "★" : "☆"}
                    </button>
                </td>
                <td class="symbol">${coin.symbol}</td>
                <td>${formatPrice(coin.price)}</td>
                <td class="${isUp ? "up" : "down"}">${sign}${coin.changePercent.toFixed(2)}%</td>
                <td>${formatPrice(coin.high)}</td>
                <td>${formatPrice(coin.low)}</td>
                <td>${formatVolume(coin.quoteVolume)}</td>
            </tr>
        `;
    });

    els.body.innerHTML = rows.join("");
}

/* ---------- 이벤트 ---------- */

els.body.addEventListener("click", (event) => {
    const button = event.target.closest(".fav-btn");
    if (button) toggleFavorite(button.dataset.symbol);
});

els.tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        currentTab = tab.dataset.tab;
        els.tabs.forEach((t) => t.classList.toggle("active", t === tab));
        render();
    });
});

els.search.addEventListener("input", render);
els.sort.addEventListener("change", render);
els.refresh.addEventListener("click", fetchCoins);

/* ---------- 시작 ---------- */

fetchCoins();
setInterval(fetchCoins, REFRESH_INTERVAL_MS);
