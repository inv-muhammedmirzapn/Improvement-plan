from functools import reduce

CONFIG = {
    "currency": "₹",
    "min_amount": 0.01,
    "large_amount": 500,
}

 
class InsufficientBalanceError(Exception):
    pass

def add_transactions(transactions, t_type, amount, description):
    t_type = t_type.strip().lower()
    if t_type not in ("deposit", "withdrawal"):
        raise ValueError(f"'{t_type}' is not a valid transaction type")
    
    amount = float(amount)
    if amount < CONFIG["min_amount"]:
        raise ValueError(f"Amount should be at least {CONFIG['currency']}{CONFIG['min_amount']}")

    if t_type == "withdrawal":
        current_balance = calculate_balance(transactions)
        if amount > current_balance:
            raise InsufficientBalanceError(
                f"Can't withdraw {CONFIG['currency']}{amount:.2f}, balance is only {CONFIG['currency']}{current_balance:.2f}"
            )
    txn = {"type": t_type, "amount": amount, "description": description or "N/A"}
    transactions.append(txn)
    return txn


def calculate_balance(transactions):
    balance = 0
    for txn in transactions:
        if txn["type"] == "deposit":
            balance += txn["amount"]
        else:
            balance -= txn["amount"]
    return balance
 
 
def calculate_totals(transactions):
    deposits = [t["amount"] for t in transactions if t["type"] == "deposit"]
    withdrawals = [t["amount"] for t in transactions if t["type"] == "withdrawal"]
    return {
        "total_deposits": sum(deposits),
        "total_withdrawals": sum(withdrawals),
    }
 
 
def find_largest_transaction(transactions):
    if not transactions:
        return None
    return max(transactions, key=lambda t: t["amount"])
 
 
def generate_summary(transactions):
    totals = calculate_totals(transactions)
    largest = find_largest_transaction(transactions)
    deposit_count = len([t for t in transactions if t["type"] == "deposit"])
    withdrawal_count = len([t for t in transactions if t["type"] == "withdrawal"])
    summary = {
        "count" : len(transactions),
        "total_deposits" : totals["total_deposits"],
        "total_withdrawals" : totals["total_withdrawals"],
        "balance" : calculate_balance(transactions),
        "largest" : largest,
        "deposit_count" : deposit_count,
        "withdrawal_count" : withdrawal_count
    }
    return summary

def print_summary(summary):
    c = CONFIG["currency"]
    print("---- SUMMARY ----")
    print(f"transactions: {summary['count']}")
    print(f"deposits: {c}{summary['total_deposits']:.2f} ({summary['deposit_count']} txns)")
    print(f"withdrawals: {c}{summary['total_withdrawals']:.2f} ({summary['withdrawal_count']} txns)")
    print(f"balance: {c}{summary['balance']:.2f}")
    if summary["largest"]:
        print(f"largest transaction: {c}{summary['largest']['amount']:.2f} - {summary['largest']['description']}")
    print("-----------------")
 
 # comprehensions, map, filter

def get_withdrawals(transactions):
    return [t for t in transactions if t["type"] == "withdrawal"]

def get_amounts(transactions):
    return [t["amount"] for t in transactions]
 
def get_formatted_amounts(transactions):
    return list(map(lambda t : f"{CONFIG['currency']} {t['amount']:.2f}", transactions))

def get_uppercase_descriptions(transactions):
    return list(map(lambda t: t["description"].upper(), transactions))

def get_by_type(transactions, t_type):
    return list(filter(lambda t:t["type"] == t_type,transactions))

def get_large_transactions(transactions):
    if not transactions:
        return None
    return max(transactions, key=lambda t: t["amount"])
 
#no max/sort

def find_second_largest(transactions):
    if len(transactions) < 2:
        return None
    amounts = get_amounts(transactions)
    first = second = float("-inf")

    for amt in amounts:
        if amt > first:
            second = first
            first = amt
        elif amt > second and amt < first:
            second = amt
    return second if second != float("-inf") else None

def find_largest_withdrawal(transactions):
    withdrawals = get_by_type(transactions, "withdrawal")
    if not withdrawals:
        return None
    
    biggest = withdrawals[0]
    for w in withdrawals[1:]:
        if w["amount"] > biggest["amount"]:
            biggest = w
    return biggest


def add_transaction(transactions):
    """Prompt user for transaction type, amount, and description, validate inputs, and store."""
    while True:
        t_type = input("Enter transaction type (deposit/withdrawal): ").strip().lower()
        if t_type not in ("deposit", "withdrawal"):
            print("Invalid transaction type. Please enter 'deposit' or 'withdrawal'.")
            continue
        break

    while True:
        try:
            amount = float(input("Enter transaction amount: "))
            if amount < CONFIG["min_amount"]:
                print(f"Invalid amount. Amount must be at least {CONFIG['currency']}{CONFIG['min_amount']}.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid numeric amount.")

    description = input("Enter transaction description (optional): ").strip()

    try:
        txn = add_transactions(transactions, t_type, amount, description)
        print(f"{txn['type'].capitalize()} of {CONFIG['currency']}{txn['amount']:.2f} added successfully.")
    except InsufficientBalanceError as e:
        print(f"Transaction failed: {e}")
    except ValueError as e:
        print(f"Transaction failed: {e}")


def display_menu():
    """Display the menu options."""
    print("\n--- Bank Transactions ---")
    print("1. Add Transaction")
    print("2. Calculate Balance")
    print("3. View Summary")
    print("4. View Transactions by Type")
    print("5. View Largest Transaction")
    print("6. Find Largest Withdrawal")
    print("7. Find Second Largest Transaction")
    print("8. Exit")


def main():
    transactions = []

    while True:
        display_menu()
        choice = input("Enter your choice (1-8): ").strip()

        if choice == "1":
            add_transaction(transactions)

        elif choice == "2":
            if not transactions:
                print("No transactions recorded yet.")
            else:
                balance = calculate_balance(transactions)
                print(f"Current Balance: {CONFIG['currency']}{balance:.2f}")

        elif choice == "3":
            if not transactions:
                print("No transactions recorded yet.")
            else:
                summary = generate_summary(transactions)
                print_summary(summary)

        elif choice == "4":
            if not transactions:
                print("No transactions recorded yet.")
            else:
                t_type = input("Enter transaction type (deposit/withdrawal): ").strip().lower()
                if t_type not in ("deposit", "withdrawal"):
                    print("Invalid transaction type. Please enter 'deposit' or 'withdrawal'.")
                else:
                    results = get_by_type(transactions, t_type)
                    if results:
                        print(f"{t_type.capitalize()} Transactions:")
                        for t in results:
                            print(f" - {CONFIG['currency']}{t['amount']:.2f} ({t['description']})")
                    else:
                        print(f"No {t_type} transactions found.")

        elif choice == "5":
            if not transactions:
                print("No transactions recorded yet.")
            else:
                largest = get_large_transactions(transactions)
                if largest:
                    desc = f" ({largest['description']})" if largest.get("description") else ""
                    print(f"Largest Transaction: {largest['type'].capitalize()} of {CONFIG['currency']}{largest['amount']:.2f}{desc}")

        elif choice == "6":
            if not transactions:
                print("No transactions recorded yet.")
            else:
                largest_w = find_largest_withdrawal(transactions)
                if largest_w:
                    print(f"Largest Withdrawal: {CONFIG['currency']}{largest_w['amount']:.2f} ({largest_w['description']})")
                else:
                    print("No withdrawal transactions found.")

        elif choice == "7":
            if not transactions:
                print("No transactions recorded yet.")
            else:
                second = find_second_largest(transactions)
                if second is not None:
                    print(f"Second Largest Transaction Amount: {CONFIG['currency']}{second:.2f}")
                else:
                    print("Not enough distinct transactions to determine the second largest amount.")

        elif choice == "8":
            print("Exiting Bank Transactions. Goodbye!")
            break

        else:
            print("Invalid choice. Please select a valid option between 1 and 8.")


if __name__ == "__main__":
    main()
 