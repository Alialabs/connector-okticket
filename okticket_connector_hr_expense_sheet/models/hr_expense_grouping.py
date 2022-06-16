# -*- coding:utf-8 -*-
# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


class ExpenseGrouping(object):
    """
        Object to implement expense classification structure

        # expenses_grouped = {
        # 'to_create': [
        #       {
        #           'name': expense sheet name,
        #           'classif_key': (analytic account id, employee id, payment mode),
        #           'expense_ids': [expense_ids],
        #       },
        #       ...
        #   ]
        # 'to_update': {
        #       expense_sheet_id: [expense_ids]
        #   }
        # }
    """
    # Variable de objeto
    _to_create_dic_templ = {
        'name': '',
        'classif_key': False,
        'expense_ids': [],
    }

    def __init__(self):
        # Variables de instancia
        self.to_create = []
        self.to_update = {}

    def add_exp_to_update_sheet(self, expense_sheet_id, expense_id):
        """
        Adds expense id to expense ids list for a given expense sheet id
        :param expense_sheet_id: int
        :param expense_id: int
        """
        if expense_sheet_id not in self.to_update.keys():
            self.to_update[expense_sheet_id] = []
        self.to_update[expense_sheet_id].append(expense_id)
        return True

    def add_exp_to_create_by_key(self, custom_key, expense_id):
        """
        Creates/updates dictionary with custom_key for classify expense_id
        :param custom_key: tuple with fields to make a key
        :param expense_id: int
        :return:
        """
        expense_added = False
        for to_create_dict in self.to_create:
            if custom_key == to_create_dict['classif_key']:
                to_create_dict['expense_ids'].append(expense_id)
                return True
        if not expense_added:
            new_exp_dict = dict(self._to_create_dic_templ)
            new_exp_dict.update({
                'name': '-'.join([str(each_key) for each_key in list(custom_key)]),
                'classif_key': custom_key,
                'expense_ids': [expense_id]
            })
            self.to_create.append(new_exp_dict)
        return True

    def empty_to_update_dict(self):
        result = True
        if self.to_update:
            result = False
        return result

    def get_to_update_dict(self):
        return self.to_update

    def empty_to_create_list(self):
        result = True
        if self.to_create:
            result = False
        return result

    def get_to_create_list(self):
        return self.to_create

    def remove_expenses_from_update_list(self, expense_sheet_id, expenses_to_remove_ids):
        """
        Removes expenses ids from update list related with expense sheet id.
        :param expense_sheet_id: int
        :param expenses_to_remove_ids: list of int
        """
        if self.to_update and expense_sheet_id in self.to_update.keys():
            for expense_to_remove_id in expenses_to_remove_ids:
                if expense_to_remove_id in self.to_update[expense_sheet_id]:
                    self.to_update[expense_sheet_id].remove(expense_to_remove_id)
            if not self.to_update[expense_sheet_id]:  # Lista vacía
                del self.to_update[expense_sheet_id]

    def merge_to_update(self, obj_to_merge):
        """
        Merges 'to_update' from obj_to_merge in self 'to_update'. Avoid duplicates.
        :param obj_to_merge: object
        """
        for to_merge_exp_sheet_id, to_merge_exp_ids in obj_to_merge.to_update.items():
            if to_merge_exp_sheet_id not in self.to_update:
                self.to_update[to_merge_exp_sheet_id] = []
            for to_merge_exp_id in to_merge_exp_ids:
                if to_merge_exp_id not in self.to_update[to_merge_exp_sheet_id]:
                    self.to_update[to_merge_exp_sheet_id].append(to_merge_exp_id)

    def merge_to_create(self, obj_to_merge):
        """
        Merges 'to_create' from obj_to_merge in self 'to_create'. Avoid duplicates.
        :param obj_to_merge: object
        """
        for to_merge_dict in obj_to_merge.to_create:
            merged = False
            for original_dict in self.to_create:
                if original_dict['classif_key'] == to_merge_dict['classif_key']:
                    # Actualiza la lista de gastos si ya existe la clave
                    for to_merge_exp_id in obj_to_merge['expense_ids']:
                        if to_merge_exp_id not in original_dict['expense_ids']:
                            original_dict['expense_ids'].append(to_merge_exp_id)
                    merged = True
                    break
            if not merged:
                # Si no existe la clave, añade el dict a la lista de to_create
                self.to_create.append(to_merge_dict)
