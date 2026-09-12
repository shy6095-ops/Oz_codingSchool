/**
 * 챌린저 55 - Javascript 1일차
 * 콘솔 기반 사칙연산 계산기
 * 변수 / 연산자 / 조건문 / 반복문 / 함수를 사용해 구현했다.
 */

// 연산자별 계산 규칙과 우선순위를 한 곳에서 관리한다.
const OPERATORS = {
    "+": { priority: 1, apply: (a, b) => a + b },
    "-": { priority: 1, apply: (a, b) => a - b },
    "*": { priority: 2, apply: (a, b) => a * b },
    "/": { priority: 2, apply: (a, b) => a / b },
};

/** 입력 문자열을 공백 기준으로 잘라 토큰 배열로 만든다. */
function tokenize(formula) {
    return formula.trim().split(/\s+/);
}

/** [숫자, 연산자, 숫자, ...] 형태인지 검사한다. */
function validate(tokens) {
    if (tokens.length < 3 || tokens.length % 2 === 0) {
        throw new Error("계산식 형식이 올바르지 않습니다. 예) 1 + 1 * 4");
    }

    for (let i = 0; i < tokens.length; i++) {
        const token = tokens[i];
        const isOperatorPosition = i % 2 === 1;

        if (isOperatorPosition && !(token in OPERATORS)) {
            throw new Error(`사용할 수 없는 연산자입니다: ${token}`);
        }
        if (!isOperatorPosition && Number.isNaN(Number(token))) {
            throw new Error(`숫자가 아닙니다: ${token}`);
        }
    }
}

/** 지정한 우선순위의 연산만 먼저 계산해 토큰 배열을 줄인다. */
function reduceOnce(tokens, priority) {
    const reduced = [tokens[0]];

    for (let i = 1; i < tokens.length; i += 2) {
        const operator = tokens[i];
        const nextNumber = tokens[i + 1];

        if (OPERATORS[operator].priority === priority) {
            const left = Number(reduced.pop());
            const right = Number(nextNumber);

            if (operator === "/" && right === 0) {
                throw new Error("0으로 나눌 수 없습니다.");
            }
            reduced.push(OPERATORS[operator].apply(left, right));
        } else {
            reduced.push(operator, nextNumber);
        }
    }

    return reduced;
}

/** 계산식 문자열을 받아 최종 결과를 돌려준다. */
function calculate(formula) {
    const tokens = tokenize(formula);
    validate(tokens);

    // 곱셈/나눗셈(2) -> 덧셈/뺄셈(1) 순서로 두 번 접는다.
    const afterMulDiv = reduceOnce(tokens, 2);
    const [result] = reduceOnce(afterMulDiv, 1);

    // 부동소수점 오차를 정리한다. (0.1 + 0.2 -> 0.3)
    return Number(result.toFixed(10));
}

/** 한 번 계산하고, 계속할지 여부를 반환한다. */
function calculateOnce() {
    const input = prompt("계산식을 입력하세요. (예: 3 + 5 * 2)");

    if (input === null || input.trim() === "") {
        console.log("입력이 없어 계산기를 종료합니다.");
        return false;
    }

    try {
        const result = calculate(input);
        console.log(`${input.trim()} = ${result}`);
    } catch (error) {
        console.log(`[에러] ${error.message}`);
    }

    return confirm("계속 계산하시겠습니까?");
}

/** 계산기 시작. 사용자가 취소할 때까지 반복한다. */
function start() {
    console.log("=== 콘솔 사칙연산 계산기 시작 ===");

    while (calculateOnce()) {
        // 사용자가 계속을 선택하는 동안 반복한다.
    }

    console.log("=== 계산기를 종료합니다 ===");
}

/** prompt 없이 준비된 예제로 검증한다. */
function runTests() {
    const cases = [
        ["3 + 5 * 2", 13],
        ["10 / 2 - 1", 4],
        ["2 * 3 * 4", 24],
        ["100 - 20 / 4", 95],
        ["1 + 2 + 3 + 4", 10],
    ];

    cases.forEach(([formula, expected]) => {
        const actual = calculate(formula);
        const mark = actual === expected ? "PASS" : "FAIL";
        console.log(`[${mark}] ${formula} = ${actual} (기대값 ${expected})`);
    });

    const errorCases = ["5 / 0", "1 +", "3 ^ 2", "a + 1"];
    errorCases.forEach((formula) => {
        try {
            calculate(formula);
            console.log(`[FAIL] ${formula} -> 에러가 발생해야 합니다.`);
        } catch (error) {
            console.log(`[PASS] ${formula} -> ${error.message}`);
        }
    });
}
