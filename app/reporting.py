"""Read-only reporting queries with inclusive dates and no payment/item join fan-out."""
from collections import defaultdict
from decimal import Decimal
import statistics

from money import money, sum_money


def date_clause(column, start, end, params):
    clause = ''
    if start:
        clause += f' AND date({column}) >= date(?)'
        params.append(start)
    if end:
        clause += f' AND date({column}) <= date(?)'
        params.append(end)
    return clause


def bill_rows(conn, start, end, search=''):
    params = []
    query = '''SELECT b.*, c.name AS customer_name, c.phone AS customer_phone,
        (SELECT COALESCE(SUM(quantity),0) FROM bill_items WHERE bill_id=b.id) AS piece_count,
        (SELECT COALESCE(SUM(ROUND(amount,2)),0) FROM payments WHERE bill_id=b.id) AS paid
        FROM bills b LEFT JOIN customers c ON c.id=b.customer_id WHERE 1=1'''
    query += date_clause('b.bill_date', start, end, params)
    if search:
        query += " AND (b.bill_no LIKE ? OR COALESCE(c.name,'Walk-in') LIKE ? OR c.phone LIKE ?)"
        params.extend([f'%{search}%'] * 3)
    rows = []
    for row in conn.execute(query + ' ORDER BY b.bill_date DESC, b.id DESC', params):
        row = dict(row)
        row['total'], row['paid'] = money(row['total']), money(row['paid'])
        row['balance'] = max(money(row['total'] - row['paid']), 0)
        rows.append(row)
    return rows


def payment_rows(conn, start, end, search=''):
    params = []
    query = '''SELECT p.*, b.bill_no, c.name AS customer_name, c.phone AS customer_phone
        FROM payments p JOIN bills b ON b.id=p.bill_id
        LEFT JOIN customers c ON c.id=b.customer_id WHERE 1=1'''
    query += date_clause('p.payment_date', start, end, params)
    if search:
        query += " AND (b.bill_no LIKE ? OR COALESCE(c.name,'Walk-in') LIKE ? OR c.phone LIKE ?)"
        params.extend([f'%{search}%'] * 3)
    return [dict(r) for r in conn.execute(query + ' ORDER BY p.payment_date DESC, p.id DESC', params)]


class ReportingQueries:
    def report_bills(self, date_from=None, date_to=None, search=''):
        with self._conn() as conn:
            return bill_rows(conn, date_from, date_to, search)

    def report_payments(self, date_from=None, date_to=None, search=''):
        with self._conn() as conn:
            return payment_rows(conn, date_from, date_to, search)

    def report_statistics(self, date_from=None, date_to=None):
        # One SQLite snapshot keeps cards and charts consistent during other writes.
        with self._conn() as conn:
            conn.execute('BEGIN')
            bills = bill_rows(conn, date_from, date_to)
            payments = payment_rows(conn, date_from, date_to)
            params = []
            query = 'SELECT amount FROM expenses WHERE 1=1'
            query += date_clause('expense_date', date_from, date_to, params)
            expenses = sum_money(r['amount'] for r in conn.execute(query, params))
            params = []
            query = '''SELECT bi.*, COALESCE(i.name,bi.item_name_snapshot) AS name,
                COALESCE(c.name,bi.category_snapshot,'Uncategorised') AS category
                FROM bill_items bi JOIN bills b ON b.id=bi.bill_id
                LEFT JOIN items i ON i.id=bi.item_id
                LEFT JOIN categories c ON c.id=i.category_id WHERE 1=1'''
            query += date_clause('b.bill_date', date_from, date_to, params)
            lines = defaultdict(list)
            for row in conn.execute(query + ' ORDER BY bi.id', params):
                lines[row['bill_id']].append(dict(row))

        daily = defaultdict(list)
        monthly = defaultdict(list)
        products = defaultdict(lambda: {'quantity': 0, 'cents': 0})
        categories = defaultdict(lambda: {'quantity': 0, 'cents': 0})
        for bill in bills:
            daily[bill['bill_date'][:10]].append(bill)
            monthly[bill['bill_date'][:7]].append(bill)
            items = lines[bill['id']]
            if not items and bill['total']:
                items = [dict(name='Unspecified items', category='Uncategorised',
                              quantity=0, subtotal=bill['total'], gst_amount=0)]
            # Allocate the billed total to its lines so historical bill-level
            # discounts/GST also reconcile to revenue. Largest remainders retain cents.
            weights = [max(Decimal(str(i['subtotal'])) + Decimal(str(i['gst_amount'] or 0)), 0) for i in items]
            if items and not sum(weights):
                weights = [Decimal(str(i['quantity'])) for i in items]
            cents = int(Decimal(str(bill['total'])) * 100)
            shares = [Decimal(cents) * w / sum(weights) for w in weights] if sum(weights) else []
            allocated = [int(v) for v in shares]
            for idx in sorted(range(len(shares)), key=lambda i: shares[i]-allocated[i], reverse=True)[:cents-sum(allocated)]:
                allocated[idx] += 1
            for item, value in zip(items, allocated):
                key = (item['name'], item['category'])
                products[key]['quantity'] += item['quantity']
                products[key]['cents'] += value
                categories[item['category']]['quantity'] += item['quantity']
                categories[item['category']]['cents'] += value

        def series(groups, key):
            return [{key: label, 'revenue': sum_money(b['total'] for b in group),
                     'bill_count': len(group)} for label, group in sorted(groups.items())]
        days = series(daily, 'date')
        values = [r['revenue'] for r in days]
        revenue = sum_money(b['total'] for b in bills)
        totals = dict(revenue=revenue, expenses=expenses, net_profit=money(revenue-expenses),
                      payments_collected=sum_money(p['amount'] for p in payments),
                      outstanding=sum_money(b['balance'] for b in bills),
                      bill_count=len(bills), pieces=sum(b['piece_count'] for b in bills),
                      avg_bill=money(revenue/len(bills)) if bills else 0,
                      mean_daily=statistics.mean(values) if values else 0,
                      median_daily=statistics.median(values) if values else 0,
                      std_daily=statistics.pstdev(values) if values else 0,
                      active_days=len(days))
        product_rows = [dict(name=name, category=category, quantity=data['quantity'], revenue=data['cents']/100)
                        for (name, category), data in products.items()]
        category_rows = [dict(category=name, quantity=data['quantity'], revenue=data['cents']/100)
                         for name, data in categories.items()]
        return dict(totals=totals, daily=days, monthly=series(monthly, 'month'),
                    products=sorted(product_rows, key=lambda r: r['revenue'], reverse=True),
                    categories=sorted(category_rows, key=lambda r: r['revenue'], reverse=True))
