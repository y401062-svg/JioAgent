"""
간단한 파이썬 계산기 (Python Calculator)
----------------------------------------
사용자로부터 입력을 받아 사칙연산을 수행하는 콘솔 기반 계산기입니다.
"""

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        return "오류: 0으로 나눌 수 없습니다!"
    return a / b

def print_menu():
    print("\n" + "=" * 30)
    print("   🧮 파이썬 계산기")
    print("=" * 30)
    print("  1. 덧셈  (+)")
    print("  2. 뺄셈  (-)")
    print("  3. 곱셈  (*)")
    print("  4. 나눗셈 (/)")
    print("  5. 종료")
    print("=" * 30)

def get_number(prompt):
    """사용자로부터 숫자를 입력받아 반환합니다."""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("  ❌ 숫자를 올바르게 입력해주세요.")

def main():
    print("🎯 파이썬 계산기에 오신 것을 환영합니다!")
    
    while True:
        print_menu()
        
        choice = input("  원하는 기능을 선택하세요 (1-5): ").strip()
        
        if choice == "5":
            print("\n  👋 계산기를 이용해 주셔서 감사합니다! 안녕히 가세요!")
            break
        
        if choice not in ("1", "2", "3", "4"):
            print("  ❌ 잘못된 선택입니다. 1에서 5 사이의 숫자를 입력해주세요.")
            continue
        
        print()
        num1 = get_number("  첫 번째 숫자를 입력하세요: ")
        num2 = get_number("  두 번째 숫자를 입력하세요: ")
        
        operations = {
            "1": ("덧셈", add(num1, num2), "+"),
            "2": ("뺄셈", subtract(num1, num2), "-"),
            "3": ("곱셈", multiply(num1, num2), "*"),
            "4": ("나눗셈", divide(num1, num2), "/"),
        }
        
        name, result, symbol = operations[choice]
        
        if isinstance(result, str):  # 오류 메시지인 경우
            print(f"\n  📌 {result}")
        else:
            print(f"\n  ✅ {name} 결과: {num1} {symbol} {num2} = {result}")

if __name__ == "__main__":
    main()