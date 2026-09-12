const form = document.getElementById("riskForm");
const resultBox = document.getElementById("result");
const errorBox = document.getElementById("error");
const bmiPreview = document.getElementById("bmiPreview");

/** 키·체중이 바뀔 때마다 BMI 를 미리 보여준다. */
function updateBmi() {
    const h = parseFloat(form.height_cm.value);
    const w = parseFloat(form.weight_kg.value);
    if (!h || !w) {
        bmiPreview.textContent = "–";
        return;
    }
    bmiPreview.textContent = (w / (h / 100) ** 2).toFixed(1);
}

form.height_cm.addEventListener("input", updateBmi);
form.weight_kg.addEventListener("input", updateBmi);
updateBmi();

/** 위험도 구간을 카드 색상 클래스로 변환한다. */
function levelClass(probability) {
    if (probability < 0.4) return "low";
    if (probability < 0.65) return "mid";
    return "high";
}

function renderRiskCards(results) {
    return Object.values(results)
        .map((r) => {
            const drivers = r.top_drivers
                .map((d) => `<li>${d.factor}<strong>+${d.impact.toFixed(2)}</strong></li>`)
                .join("");
            return `
                <article class="risk-card ${levelClass(r.probability)}">
                    <p class="name">${r.label} 위험도</p>
                    <p class="pct">${r.percent}%</p>
                    <span class="level">${r.risk}</span>
                    <div class="track"><div class="fill" style="width:${r.percent}%"></div></div>
                    <ul class="drivers">${drivers || "<li>주요 위험요인 없음</li>"}</ul>
                    <p class="auc">모델 AUC ${r.model_auc}</p>
                </article>`;
        })
        .join("");
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = "계산 중…";

    // 체크박스는 0/1 로, 나머지는 숫자로 변환해서 보낸다.
    const payload = {};
    for (const [key, value] of new FormData(form).entries()) {
        payload[key] = Number(value);
    }
    payload.family_history = form.family_history.checked ? 1 : 0;
    payload.smoker = form.smoker.checked ? 1 : 0;

    try {
        const res = await fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(
                Array.isArray(detail.detail)
                    ? detail.detail.map((d) => d.msg).join(", ")
                    : detail.detail || `요청 실패 (${res.status})`
            );
        }

        const data = await res.json();

        document.getElementById("riskCards").innerHTML = renderRiskCards(data.results);

        const flagBox = document.getElementById("flagBox");
        const flags = document.getElementById("flags");
        flags.innerHTML = data.clinical_flags
            .map((f) => `<li class="${f.level}">${f.text}</li>`)
            .join("");
        flagBox.hidden = data.clinical_flags.length === 0;

        document.getElementById("tips").innerHTML = data.recommendations
            .map((t) => `<li>${t}</li>`)
            .join("");

        document.getElementById("disclaimer").textContent = data.disclaimer;

        resultBox.hidden = false;
        resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
        errorBox.textContent = err.message;
        errorBox.hidden = false;
    } finally {
        button.disabled = false;
        button.textContent = "위험도 계산";
    }
});

/** 모델 버전을 상단에 표시한다. */
fetch("/api/model")
    .then((res) => res.json())
    .then((m) => {
        document.getElementById("modelVersion").textContent = `모델 v${m.version}`;
    })
    .catch(() => {
        document.getElementById("modelVersion").textContent = "모델 정보 없음";
    });
