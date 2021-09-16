# -*- coding: utf-8 -*-

from .ticket_connector import OkTicketOpenConnector


# ==================================================================================
#   Run program
# ==================================================================================

if __name__ == "__main__":
    okticketconn = OkTicketOpenConnector()
    print("--- INICIANDO OkTicket Open Connector...")
    state = True
    while state:
        okticketconn.auth_test()
        okticketconn.find_expenses()
        okticketconn.find_expense_by_id('5cab22b28697183419600513')
        state = False
    print ("\n--- STOPPED ---")
