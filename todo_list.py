"""
📋 간단한 할 일 목록 (Todo List) 관리 프로그램
- 기능: 할 일 추가, 완료 처리, 삭제, 목록 보기
"""

import json
import os
from datetime import datetime

DATA_FILE = "todos.json"


def load_todos():
    """저장된 할 일 목록을 불러옵니다."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_todos(todos):
    """할 일 목록을 파일에 저장합니다."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def add_todo(title):
    """새로운 할 일을 추가합니다."""
    todos = load_todos()
    todo = {
        "id": len(todos) + 1,
        "title": title,
        "done": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    todos.append(todo)
    save_todos(todos)
    print(f"✅ 할 일 추가됨: '{title}' (ID: {todo['id']})")


def list_todos():
    """모든 할 일을 표시합니다."""
    todos = load_todos()
    if not todos:
        print("📭 할 일이 없습니다. 새로운 할 일을 추가해보세요!")
        return

    print("\n" + "=" * 40)
    print("📋 할 일 목록")
    print("=" * 40)
    for todo in todos:
        status = "✅" if todo["done"] else "⬜"
        print(f"  {status} [ID:{todo['id']}] {todo['title']}")
        print(f"     생성: {todo['created_at']}")
    print("=" * 40 + "\n")


def complete_todo(todo_id):
    """할 일을 완료 상태로 변경합니다."""
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = True
            save_todos(todos)
            print(f"🎉 할 일 완료! '{todo['title']}' (ID: {todo_id})")
            return
    print(f"❌ ID {todo_id}에 해당하는 할 일이 없습니다.")


def delete_todo(todo_id):
    """할 일을 삭제합니다."""
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todos.remove(todo)
            save_todos(todos)
            print(f"🗑️ 할 일 삭제됨: '{todo['title']}' (ID: {todo_id})")
            return
    print(f"❌ ID {todo_id}에 해당하는 할 일이 없습니다.")


def show_menu():
    """메뉴를 표시합니다."""
    print("\n" + "★" * 30)
    print("  📋 Todo List Manager")
    print("★" * 30)
    print("  1. 할 일 추가")
    print("  2. 할 일 목록 보기")
    print("  3. 할 일 완료 처리")
    print("  4. 할 일 삭제")
    print("  5. 종료")
    print("★" * 30)


def main():
    """메인 실행 함수"""
    print("\n🎯 Todo List Manager에 오신 것을 환영합니다!")
    print("간단하게 할 일을 관리해보세요.")

    while True:
        show_menu()
        choice = input("\n👉 원하는 기능을 선택하세요 (1-5): ").strip()

        if choice == "1":
            title = input("📝 추가할 할 일: ").strip()
            if title:
                add_todo(title)
            else:
                print("⚠️ 내용을 입력해주세요.")

        elif choice == "2":
            list_todos()

        elif choice == "3":
            try:
                todo_id = int(input("✅ 완료할 할 일 ID: ").strip())
                complete_todo(todo_id)
            except ValueError:
                print("⚠️ 숫자로 ID를 입력해주세요.")

        elif choice == "4":
            try:
                todo_id = int(input("🗑️ 삭제할 할 일 ID: ").strip())
                delete_todo(todo_id)
            except ValueError:
                print("⚠️ 숫자로 ID를 입력해주세요.")

        elif choice == "5":
            print("👋 프로그램을 종료합니다. 좋은 하루 되세요!")
            break

        else:
            print("⚠️ 1에서 5 사이의 숫자를 입력해주세요.")


if __name__ == "__main__":
    main()