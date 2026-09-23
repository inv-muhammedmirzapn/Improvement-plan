def add_expense(expenses):
    """Prompt user for expense amount and category, validate inputs, and store."""
    while True:
        try:
            amount = float(input("Enter expense amount: "))
            if amount <= 0:
                print("Invalid amount. Amount must be greater than zero.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid numeric amount.")

    while True:
        category = input("Enter expense category: ").strip()
        if not category:
            print("Invalid category. Category cannot be empty.")
            continue
        break

    expense = {"amount": amount, "category": category}
    expenses.append(expense)
    print(f"Expense of INR {amount:.2f} in '{category}' added successfully.")


def calculate_total_expenses(expenses):
    """Calculate and return the total of all expenses."""
    return sum(expense["amount"] for expense in expenses)


def find_highest_expense(expenses):
    """Find and return the expense with the highest amount, or None if empty."""
    if not expenses:
        return None
    return max(expenses, key=lambda x: x["amount"])


def calculate_category_spending(expenses):
    """Calculate and return total spending for each category."""
    spending = {}
    for expense in expenses:
        category = expense["category"]
        spending[category] = spending.get(category, 0.0) + expense["amount"]
    return spending


def search_expenses_by_category(expenses, category):
    """Search and return all expenses matching the specified category."""
    category_lower = category.strip().lower()
    return [e for e in expenses if e["category"].lower() == category_lower]


def display_menu():
    """Display the menu options."""
    print("\n--- Expense Tracker ---")
    print("1. Add Expense")
    print("2. Calculate Total Expenses")
    print("3. Find Highest Expense")
    print("4. Calculate Spending by Category")
    print("5. Search Expenses by Category")
    print("6. Exit")


def main():
    expenses = []

    while True:
        display_menu()
        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            add_expense(expenses)

        elif choice == "2":
            if not expenses:
                print("No expenses recorded yet.")
            else:
                total = calculate_total_expenses(expenses)
                print(f"Total Expenses: INR {total:.2f}")

        elif choice == "3":
            highest = find_highest_expense(expenses)
            if highest is None:
                print("No expenses recorded yet.")
            else:
                print(f"Highest Expense: INR {highest['amount']:.2f} ({highest['category']})")

        elif choice == "4":
            if not expenses:
                print("No expenses recorded yet.")
            else:
                category_totals = calculate_category_spending(expenses)
                print("Total Spending by Category:")
                for category, total in category_totals.items():
                    print(f" - {category}: INR {total:.2f}")

        elif choice == "5":
            if not expenses:
                print("No expenses recorded yet.")
            else:
                search_category = input("Enter category to search: ").strip()
                if not search_category:
                    print("Category cannot be empty.")
                else:
                    results = search_expenses_by_category(expenses, search_category)
                    if results:
                        print(f"Expenses in category '{search_category}':")
                        for item in results:
                            print(f" - INR {item['amount']:.2f} ({item['category']})")
                    else:
                        print(f"No expenses found for category '{search_category}'.")

        elif choice == "6":
            print("Exiting Expense Tracker. Goodbye!")
            break

        else:
            print("Invalid choice. Please select a valid option between 1 and 6.")


if __name__ == "__main__":
    main()
