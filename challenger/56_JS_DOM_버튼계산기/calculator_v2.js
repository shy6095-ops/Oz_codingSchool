/**
 * 챌린저 56 - Javascript 2일차
 * DOM 조작과 이벤트로 만드는 버튼 계산기
 * - ON/OFF 전원 버튼, C(전체 삭제), <-(한 글자 삭제), +/-(부호 전환)
 * - 곱셈/나눗셈 우선순위 적용, 0으로 나누기 방어
 * - 키보드 입력도 함께 지원
 */

const OPERATORS = {
    "+": { priority: 1, apply: (a, b) => a + b },
    "-": { priority: 1, apply: (a, b) => a - b },
    "*": { priority: 2, apply: (a, b) => a * b },
    "/": { priority: 2, apply: (a, b) => a / b },
};

const display = document.getElementById("display");
const history = document.getElementById("history");
const powerBtn = document.getElementById("powerBtn");

const state = {
    poweredOn: true,
    formula: "",
    justCalculated: false,
};

/* ---------- 계산 로직 ---------- */

function reduceOnce(tokens, priority) {
    const reduced = [tokens[0]];

    for (let i = 1; i < tokens.length; i += 2) {
        const operator = tokens[i];
        const nextNumber = tokens[i + 1];

        if (OPERATORS[operator].priority === priority) {
            const left = Number(reduced.pop());
            const right = Number(nextNumber);

            if (operator === "/" && right === 0) {
                throw new Error("0으로 나눌 수 없음");
            }
            reduced.push(OPERATORS[operator].apply(left, right));
        } else {
            reduced.push(operator, nextNumber);
        }
    }

    return reduced;
}

function evaluate(formula) {
    const tokens = formula.trim().split(/\s+/);

    if (tokens.length < 3 || tokens.length % 2 === 0) {
        throw new Error("계산식 오류");
    }

    for (let i = 0; i < tokens.length; i++) {
        const isOperatorPosition = i % 2 === 1;
        if (isOperatorPosition && !(tokens[i] in OPERATORS)) throw new Error("계산식 오류");
        if (!isOperatorPosition && Number.isNaN(Number(tokens[i]))) throw new Error("계산식 오류");
    }

    const afterMulDiv = reduceOnce(tokens, 2);
    const [result] = reduceOnce(afterMulDiv, 1);

    if (!Number.isFinite(result)) throw new Error("계산식 오류");
    return Number(result.toFixed(10));
}

/* ---------- 화면 출력 ---------- */

function render() {
    display.value = state.formula === "" ? "0" : state.formula;
}

function showError(message) {
    history.textContent = message;
    state.formula = "";
    state.justCalculated = false;
    render();
}

/* ---------- 버튼 동작 ---------- */

function pressNumber(value) {
    if (!state.poweredOn) return;

    if (state.justCalculated) {
        state.formula = "";
        state.justCalculated = false;
        history.textContent = "";
    }

    // 소수점은 현재 입력 중인 숫자에 하나만 허용한다.
    if (value === ".") {
        const currentNumber = state.formula.split(" ").pop();
        if (currentNumber.includes(".")) return;
        if (currentNumber === "") value = "0.";
    }

    state.formula += value;
    render();
}

function pressOperator(operator) {
    if (!state.poweredOn || state.formula === "") return;

    state.justCalculated = false;
    history.textContent = "";

    // 연산자를 연달아 누르면 마지막 연산자를 교체한다.
    if (state.formula.endsWith(" ")) {
        state.formula = state.formula.slice(0, -3);
    }

    state.formula += ` ${operator} `;
    render();
}

function pressClear() {
    if (!state.poweredOn) return;
    state.formula = "";
    state.justCalculated = false;
    history.textContent = "";
    render();
}

function pressBackspace() {
    if (!state.poweredOn) return;

    state.justCalculated = false;
    state.formula = state.formula.endsWith(" ")
        ? state.formula.slice(0, -3)   // " + " 처럼 연산자는 3글자씩 지운다.
        : state.formula.slice(0, -1);

    render();
}

function pressSign() {
    if (!state.poweredOn) return;

    const parts = state.formula.split(" ");
    const last = parts.pop();
    if (last === "" || Number.isNaN(Number(last))) return;

    parts.push(String(-Number(last)));
    state.formula = parts.join(" ");
    render();
}

function pressEqual() {
    if (!state.poweredOn || state.formula === "") return;

    const expression = state.formula.trim();

    try {
        const result = evaluate(expression);
        history.textContent = `${expression} =`;
        state.formula = String(result);
        state.justCalculated = true;
        render();
    } catch (error) {
        showError(error.message);
    }
}

function togglePower() {
    state.poweredOn = !state.poweredOn;
    powerBtn.classList.toggle("on", state.poweredOn);

    document.querySelectorAll("button:not(.power)").forEach((button) => {
        button.disabled = !state.poweredOn;
    });

    state.formula = "";
    state.justCalculated = false;
    history.textContent = "";

    if (state.poweredOn) {
        display.classList.remove("off");
        render();
    } else {
        display.classList.add("off");
        display.value = "";
    }
}

/* ---------- 이벤트 연결 ---------- */

const ACTIONS = {
    clear: pressClear,
    backspace: pressBackspace,
    sign: pressSign,
    equal: pressEqual,
};

document.querySelector(".buttons").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;

    if (button.classList.contains("power")) return togglePower();
    if (button.dataset.number) return pressNumber(button.dataset.number);
    if (button.dataset.operator) return pressOperator(button.dataset.operator);
    if (button.dataset.action) return ACTIONS[button.dataset.action]();
});

document.addEventListener("keydown", (event) => {
    const key = event.key;

    if (/^[0-9.]$/.test(key)) return pressNumber(key);
    if (key in OPERATORS) return pressOperator(key);
    if (key === "Enter" || key === "=") return pressEqual();
    if (key === "Backspace") return pressBackspace();
    if (key === "Escape" || key.toLowerCase() === "c") return pressClear();
});

render();
