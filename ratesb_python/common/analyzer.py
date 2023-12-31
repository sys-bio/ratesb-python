from dataclasses import dataclass
import json
import sys
import os
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)

from custom_classifier import _CustomClassifier
# from SBMLKinetics.common.simple_sbml import SimpleSBML
# from SBMLKinetics.common.reaction import Reaction
from typing import List, Dict, Optional
from SBMLKinetics.common.simple_sbml import SimpleSBML
import util
from results import Results

import antimony
import libsbml
import os
import re
import sympy as sp

from typing import List, Any

ZERO = "ZERO"
UNDR1 = "UNDR1"
UNDR2 = "UNDR2"
UNDR3 = "UNDR3"
UNDR_A1 = "UNDR-A1"
UNDR_A2 = "UNDR-A2"
UNDR_A3 = "UNDR-A3"
BIDR11 = "BIDR11"
BIDR12 = "BIDR12"
BIDR21 = "BIDR21"
BIDR22 = "BIDR22"
BIDR_A11 = "BIDR-A11"
BIDR_A12 = "BIDR-A12"
BIDR_A21 = "BIDR-A21"
BIDR_A22 = "BIDR-A22"
MM = "MM"
MM_CAT = "MMcat"
AMM = "AMM"
IMM = "IMM"
RMM = "RMM"
RMM_CAT = "RMMcat"
HILL = "Hill"

NON_MM_KEYS = [
    ZERO, UNDR1, UNDR2, UNDR3, UNDR_A1, UNDR_A2, UNDR_A3,
    BIDR11, BIDR12, BIDR21, BIDR22, BIDR_A11, BIDR_A12, BIDR_A21, BIDR_A22
]

MM_KEYS = [MM, MM_CAT, AMM, IMM, RMM, RMM_CAT]

UNDR_KEYS = [UNDR1, UNDR2, UNDR3]

UNDR_A_KEYS = [UNDR_A1, UNDR_A2, UNDR_A3]

BIDR_ALL_KEYS = [BIDR11, BIDR12, BIDR21, BIDR22,
                 BIDR_A11, BIDR_A12, BIDR_A21, BIDR_A22]

MM_CAT_KEYS = [MM_CAT, AMM, IMM, RMM_CAT]

UNDR_SBOS = [41, 43, 44, 45, 47, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 140, 141, 142, 143, 144, 145, 146, 163, 166, 333, 560, 561, 562, 563, 564, 430, 270, 458,
             275, 273, 379, 440, 443, 451, 454, 456, 260, 271, 378, 387, 262, 265, 276, 441, 267, 274, 444, 452, 453, 455, 457, 386, 388, 442, 277, 445, 446, 447, 448, 266, 449, 450]

UNDR_A_SBOS = [41, 43, 44, 45, 47, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
               140, 141, 142, 143, 144, 145, 146, 163, 166, 333, 560, 561, 562, 563, 564]

BI_SBOS = [42, 69, 78, 88, 109, 646, 70, 71, 74, 79, 80, 81, 84, 89, 99, 110, 120, 130, 72, 73, 75, 76, 77, 82, 83, 85, 86, 87, 90, 91, 92, 95, 100, 101, 102, 105, 111, 112,
           113, 116, 121, 122, 123, 126, 131, 132, 133, 136, 93, 94, 96, 97, 98, 103, 104, 106, 107, 108, 114, 115, 117, 118, 119, 124, 125, 127, 128, 129, 134, 135, 137, 138, 139]

MM_SBOS = [28, 29, 30, 31, 199]

MM_CAT_SBOS = [28, 29, 30, 31, 199, 430, 270, 458, 275, 273, 379, 440, 443, 451, 454, 456, 260, 271, 378, 387,
               262, 265, 276, 441, 267, 274, 444, 452, 453, 455, 457, 386, 388, 442, 277, 445, 446, 447, 448, 266, 449, 450]

HILL_SBOS = [192, 195, 198]

ALL_CHECKS = []
ERROR_CHECKS = []
WARNING_CHECKS = []
for i in range(1, 3):
    ALL_CHECKS.append(i)
    ERROR_CHECKS.append(i)
for i in range(1001, 1007):
    ALL_CHECKS.append(i)
    WARNING_CHECKS.append(i)
for i in range(1010, 1011):
    ALL_CHECKS.append(i)
    WARNING_CHECKS.append(i)
for i in range(1020, 1023):
    ALL_CHECKS.append(i)
    WARNING_CHECKS.append(i)
for i in range(1030, 1038):
    ALL_CHECKS.append(i)
    WARNING_CHECKS.append(i)
for i in range(1040, 1045):
    ALL_CHECKS.append(i)
    WARNING_CHECKS.append(i)
    
with open(os.path.join(os.path.dirname(__file__), "messages.json")) as file:
    MESSAGES = json.load(file)

@dataclass
class ReactionData:
    reaction_id: str
    kinetics: str
    kinetics_sim: str
    reactant_list: List[str]
    product_list: List[str]
    species_in_kinetic_law: List[str]
    parameters_in_kinetic_law: List[str]
    ids_list: List[str]
    sorted_species: List[str]
    boundary_species: List[str]
    parameters_in_kinetic_law_only: List[str]
    compartment_in_kinetic_law: List[str]
    is_reversible: bool
    sbo_term: int
    codes: List[int]
    non_constant_params: List[str]


class Analyzer:
    """
    The Analyzer class analyzes SBML models to check if the rate laws are following 
    some rules. It uses sympy for processing mathematical symbol expressions, libsbmlpython 
    for processing SBML models, and SBMLKinetics for analyzing SBML models and classifying 
    rate laws. The class can return errors and warnings based on the specified checks.
    """
    
    @staticmethod
    def list_all_checks():
        """
        Returns a string representation of all the checks.
        """
        ret = ""
        ret += "Error checks:\n"
        for code in ERROR_CHECKS:
            ret += str(code) + ": " + Analyzer.list_check(code) + "\n"
        ret += "\nWarning checks:\n"
        for code in WARNING_CHECKS:
            ret += Analyzer.list_check(code) + "\n"
        return ret
    
    @staticmethod
    def list_check(code):
        """
        Returns a string representation of the check corresponding to the provided code.

        Args:
            code (int): The code of the check.
        """
        ret = str(code) + ": "
        if code not in ALL_CHECKS:
            return None
        if code < 1000:
            ret += MESSAGES["errors"][str(code)]
        else:
            ret += MESSAGES["warnings"][str(code)]
        return ret
        

    def __init__(self, model_str: str, rate_law_classifications_path: str=None):
        """
        Initializes the Analyzer class.

        Args:
            model_str (str): Path to the model file, or the string representation of model.
            rate_law_classifications_path (str): Path to the rate law classification file.
            customized rate law classification.

        Examples:
            import Analyzer from ratesb_python.common.analyzer
            analyzer = Analyzer("path/to/biomodel.xml", "path/to/rate_laws.json")
            analyzer.check_all()
            results = analyzer.results
            print(str(results))
            str(results)
        """
        # check if parameters are strings
        if not isinstance(model_str, str):
            raise ValueError("Invalid model_str format, should be string.")
        if rate_law_classifications_path and not isinstance(rate_law_classifications_path, str):
            raise ValueError("Invalid rate_law_classifications_path format, should be string.")
        # check if the model_str is sbml
        if '<?xml' in model_str:
            if '<sbml' not in model_str:
                raise ValueError("Invalid SBML model.")
            else:
                xml = model_str
        else:
            # model_str is not sbml
            load_int = antimony.loadAntimonyString(model_str)
            if load_int > 0:
                xml = antimony.getSBMLString()
            elif model_str.endswith('.ant') or model_str.endswith('.txt') or model_str.endswith('.xml'):
                # model_str is path to model
                xml = ''
                if model_str.endswith('.ant') or model_str.endswith('.txt'):
                    ant = util.get_model_str(model_str, False)
                    load_int = antimony.loadAntimonyString(ant)
                    if load_int > 0:
                        xml = antimony.getSBMLString()
                    else:
                        raise ValueError("Invalid Antimony model.")
                else:
                    xml = util.get_model_str(model_str, True)
            else:
                raise ValueError("Invalid model_str format, should be SBML or Antimony string, or path to model file.")
        reader = libsbml.SBMLReader()
        document = reader.readSBMLFromString(xml)
        util.checkSBMLDocument(document)
        self.model = document.getModel()
        self.simple = SimpleSBML(self.model)
        self.custom_classifier = None
        self.default_classifications = {}
        self.custom_classifications = {}
        self.results = Results()
        self.default_classifier = _CustomClassifier(os.path.join(
            os.path.dirname(__file__), "default_classifier.json"))

        if rate_law_classifications_path:
            self.custom_classifier = _CustomClassifier(
                rate_law_classifications_path)
            if len(self.custom_classifier.warning_message) > 0:
                print(self.custom_classifier.warning_message)

    def check_except(self, excluded_codes: Optional[List[int]]=[]):
        """
        Performs all checks except the ones corresponding to the provided list of error or warning codes.

        Args:
            excluded_codes (Optional[List[int]]): List of codes of the checks to exclude. If None, all checks are performed.

        Updates:
            The results of the check(s) to self.results.
        """
        self.checks(list(set(ALL_CHECKS) - set(excluded_codes)))

    def check_all(self):
        """
        Performs all checks.

        Updates:
            The results of the check_all to self.results.
        """
        self.check_except([])

    def checks(self, codes):
        """
        Performs multiple checks based on the provided list of error or warning codes. If no codes are provided, 
        all checks are performed.

        Args:
            codes (List[int]): List of codes of the checks to perform.

        Updates:
            The results of the checks to self.results.
        """
            
        self.default_classifications = {}
        self.custom_classifications = {}
        self.results.clear_results()

        for reaction in self.simple.reactions:
            reaction.kinetic_law.formula = reaction.kinetic_law.formula.replace(
                '^', '**')
            ids_list = list(dict.fromkeys(reaction.kinetic_law.symbols))

            libsbml_kinetics = reaction.kinetic_law.libsbml_kinetics
            sbo_term = -1
            if libsbml_kinetics:
                sbo_term = libsbml_kinetics.getSBOTerm()

            reaction_id = reaction.getId()
            sorted_species = self._get_sorted_species(reaction.reaction)
            species_list, parameter_list, compartment_list, kinetics, kinetics_sim = self._preprocess_reactions(
                reaction)
            reactant_list, product_list = self._extract_kinetics_details(
                reaction)
            species_in_kinetic_law, parameters_in_kinetic_law_only, compartment_in_kinetic_law, others_in_kinetic_law = self._identify_parameters_in_kinetics(
                ids_list, species_list, parameter_list, compartment_list)
            boundary_species = self._get_boundary_species(
                reactant_list, product_list)
            non_constant_params = self._get_non_constant_params(parameters_in_kinetic_law_only)
                

            data = ReactionData(
                reaction_id=reaction_id,
                kinetics=kinetics,
                kinetics_sim=kinetics_sim,
                reactant_list=reactant_list,
                product_list=product_list,
                species_in_kinetic_law=species_in_kinetic_law,
                parameters_in_kinetic_law=parameters_in_kinetic_law_only + others_in_kinetic_law,
                ids_list=ids_list,
                sorted_species=sorted_species,
                boundary_species=boundary_species,
                parameters_in_kinetic_law_only=parameters_in_kinetic_law_only,
                compartment_in_kinetic_law=compartment_in_kinetic_law,
                is_reversible=reaction.reaction.getReversible(),
                sbo_term=sbo_term,
                codes=codes,
                non_constant_params=non_constant_params
            )

            self._set_kinetics_type(**data.__dict__)
            if 1 in codes:
                self._check_empty_kinetics(**data.__dict__)
            if 2 in codes:
                self._check_floating_species(**data.__dict__)
            if 1001 in codes:
                self._check_pure_number(**data.__dict__)
            if 1002 in codes:
                self._check_unrecognized_rate_law(**data.__dict__)
            if 1003 in codes:
                self._check_flux_increasing_with_reactant(**data.__dict__)
            if 1004 in codes:
                self._check_flux_decreasing_with_product(**data.__dict__)
            if 1005 in codes:
                self._check_boundary_floating_species(**data.__dict__)
            if 1006 in codes:
                self._check_constant_parameters(**data.__dict__)
            if 1010 in codes:
                self._check_irreversibility(**data.__dict__)
            if 1020 in codes or 1021 in codes or 1022 in codes:
                self._check_naming_conventions(**data.__dict__)
            if any(isinstance(num, int) and 1030 <= num <= 1037 for num in codes):
                self._check_formatting_conventions(**data.__dict__)
            if any(isinstance(num, int) and 1040 <= num <= 1044 for num in codes):
                self._check_sboterm_annotations(**data.__dict__)

            # self._check_empty_kinetics(**kwargs)
            # self._check_boundary_floating_species(**kwargs)

    def _get_sorted_species(self, reaction):
        sorted_species_reference = [reaction.getReactant(n) for n in range(
            reaction.getNumReactants())] + [reaction.getProduct(n) for n in range(reaction.getNumProducts())]
        sorted_species = []
        for species_reference in sorted_species_reference:
            sorted_species.append(species_reference.getSpecies())
        return sorted_species

    def _preprocess_reactions(self, reaction):
        # Extract and process necessary data from the reaction
        species_num = self.model.getNumSpecies()
        parameter_num = self.model.getNumParameters()
        compartment_num = self.model.getNumCompartments()

        species_list = [self.model.getSpecies(
            i).getId() for i in range(species_num)]
        parameter_list = [self.model.getParameter(
            i).getId() for i in range(parameter_num)]
        compartment_list = [self.model.getCompartment(
            i).getId() for i in range(compartment_num)]

        kinetics = reaction.kinetic_law.expanded_formula

        try:
            kinetics_sim = str(sp.simplify(kinetics))
        except:
            kinetics_sim = kinetics

        return species_list, parameter_list, compartment_list, kinetics, kinetics_sim

    def _extract_kinetics_details(self, reaction):
        reactant_list = [r.getSpecies() for r in reaction.reactants]
        product_list = [p.getSpecies() for p in reaction.products]
        return reactant_list, product_list

    def _identify_parameters_in_kinetics(self, ids_list, species_list, parameter_list, compartment_list):
        species_in_kinetic_law = []
        parameters_in_kinetic_law_only = []
        compartment_in_kinetic_law = []
        others_in_kinetic_law = []

        for id in ids_list:
            if id in species_list:
                species_in_kinetic_law.append(id)
            elif id in parameter_list:
                parameters_in_kinetic_law_only.append(id)
            elif id in compartment_list:
                compartment_in_kinetic_law.append(id)
                others_in_kinetic_law.append(id)
            else:
                others_in_kinetic_law.append(id)

        return species_in_kinetic_law, parameters_in_kinetic_law_only, compartment_in_kinetic_law, others_in_kinetic_law

    def _get_boundary_species(self, reactant_list, product_list):
        boundary_species = [reactant for reactant in reactant_list if self.model.getSpecies(
            reactant).getBoundaryCondition()]
        boundary_species += [product for product in product_list if self.model.getSpecies(
            product).getBoundaryCondition()]
        return boundary_species

    def _get_non_constant_params(self, parameters_in_kinetic_law_only):
        non_constant_params = []
        for param in parameters_in_kinetic_law_only:
            libsbml_param = self.model.getParameter(param)
            if not libsbml_param.getConstant():
                non_constant_params.append(param)
        return non_constant_params

    def _set_kinetics_type(self, **kwargs):
        reaction_id = kwargs["reaction_id"]
        self.default_classifications[reaction_id] = self.default_classifier.custom_classify(
            is_default=True, **kwargs)
        if self.custom_classifier:
            self.custom_classifications[reaction_id] = self.custom_classifier.custom_classify(
                **kwargs)

    def _check_empty_kinetics(self, **kwargs):
        """
        Checks if the given reaction has an empty kinetic law.
        Code: 1

        Args:
            reaction_id (str): The reaction's id'.
            kinetics (str): The kinetic law

        Adds:
            An error message to results specifying that no rate law was entered for the reaction.
        """
        reaction_id = kwargs["reaction_id"]
        kinetics = kwargs["kinetics"]
        if len(kinetics.replace(' ', '')) == 0:
            self.results.add_message(
                reaction_id, 1, f"No rate law entered.", False)

    def _check_floating_species(self, **kwargs):
        """
        Checks if all reactants in the rate law of the given reaction are defined as species, excluding boundary species.
        Code: 2

        Args:
            reaction_id (str): The reaction's id'.
            species_in_kinetic_law (list): A list of species present in the rate law.
            reactant_list (list): A list of reactants for the reaction.
            boundary_species (list): A list of boundary species in the model.

        Adds:
            An error message to results specifying the missing reactants that are expected in the rate law.
        """
        reaction_id = kwargs["reaction_id"]
        species_in_kinetic_law = kwargs["species_in_kinetic_law"]
        reactant_list = kwargs["reactant_list"]
        boundary_species = kwargs["boundary_species"]

        floating_species = []
        for reactant in reactant_list:
            if reactant not in species_in_kinetic_law:
                if reactant not in boundary_species:
                    floating_species.append(reactant)
        if len(floating_species) > 0:
            floating_species = ",".join(floating_species)
            self.results.add_message(
                reaction_id, 2, f"Expecting reactants in rate law: {floating_species}", False)

    def _check_pure_number(self, **kwargs):
        """
        Checks if the rate law contains only number
        Code: 1001

        Args:
            reaction_id (str): The reaction's id'.
            kinetics_sim: string-simplified kinetics

        Adds:
            A warning message to results specifying that the rate law contains only numbers.
        """
        reaction_id = kwargs["reaction_id"]
        kinetics_sim = kwargs["kinetics_sim"]
        try:
            float(kinetics_sim)
            self.results.add_message(
                reaction_id, 1001, "Rate law contains only number.")
        except:
            return

    def _check_unrecognized_rate_law(self, **kwargs):
        """
        Checks if the rate law from the standard and custom list (if given) is recognized
        Code: 1002

        Args:
            reaction_id (str): The reaction's id'.

        Adds:
            A warning message to results specifying that the rate law is unrecognized.
        """
        reaction_id = kwargs["reaction_id"]
        if len(self.custom_classifications) > 0:
            if not (any(self.default_classifications[reaction_id].values()) or any(self.custom_classifications[reaction_id].values())):
                self.results.add_message(
                    reaction_id, 1002, "Unrecognized rate law from the standard list and the custom list.")
        else:
            if not any(self.default_classifications[reaction_id].values()):
                self.results.add_message(
                    reaction_id, 1002, "Unrecognized rate law from the standard list.")

    def _check_flux_increasing_with_reactant(self, **kwargs):
        """
        Checks if the flux is increasing as the reactant increases.
        Code: 1003

        Args:
            reaction_id (str): The reaction's id'.
            reactant_list (str): List of reactants in reaction
            kinetics (str): the kinetic law

        Adds:
            A warning message to results specifying if the flux is not increasing as reactant increases.
        """
        reaction_id = kwargs["reaction_id"]
        reactant_list = kwargs["reactant_list"]
        kinetics = kwargs["kinetics"]

        if not util.check_symbols_derivative(sp.sympify(kinetics), reactant_list):
            self.results.add_message(
                reaction_id, 1003, "Flux is not increasing as reactant increases.")

    def _check_flux_decreasing_with_product(self, **kwargs):
        """
        Checks if the flux is increasing as the product decreases.
        Code: 1004

        Args:
            reaction_id (str): The reaction's id'.
            is_reversible (bool): the reaction's reversibility
            product_list (list): List of products in reaction
            kinetics (str): the kinetic law

        Adds:
            A warning message to results specifying if the flux is not decreasing as product increases.
        """
        reaction_id = kwargs["reaction_id"]
        is_reversible = kwargs["is_reversible"]
        product_list = kwargs["product_list"]
        kinetics = kwargs["kinetics"]

        if is_reversible:
            if not util.check_symbols_derivative(sp.sympify(kinetics), product_list, False):
                self.results.add_message(
                    reaction_id, 1004, "Flux is not decreasing as product increases.")

    def _check_boundary_floating_species(self, **kwargs):
        """
        Checks if any reactant in the rate law of the given reaction is a boundary species.
        Code: 1005

        Args:
            reaction_id (str): The reaction's id'.
            species_in_kinetic_law: A list of species present in the rate law.
            reactant_list: A list of reactants for the reaction.
            boundary_species: A list of boundary species in the model.

        Adds:
            A warning message to results specifying the boundary species reactants found in the rate law.
        """
        reaction_id = kwargs["reaction_id"]
        species_in_kinetic_law = kwargs["species_in_kinetic_law"]
        reactant_list = kwargs["reactant_list"]
        boundary_species = kwargs["boundary_species"]

        boundary_floating_species = []
        for reactant in reactant_list:
            if reactant not in species_in_kinetic_law:
                if reactant in boundary_species:
                    boundary_floating_species.append(reactant)
        if len(boundary_floating_species) > 0:
            boundary_floating_species = ",".join(boundary_floating_species)
            self.results.add_message(
                reaction_id, 1005, f"Expecting boundary species reactant in rate law: {boundary_floating_species}")

    def _check_constant_parameters(self, **kwargs):
        """
        Checks if the parameters in the rate law are constants.
        Code: 1006
        TODO remove libsbml dependency

        Args:
            reaction_id (str): The reaction's id'.
            parameters_in_kinetic_law_only (list): the parameters in kinetic law

        Adds:
            A warning message to results specifying if the parameters are not constants.
        """
        reaction_id = kwargs["reaction_id"]
        parameters_in_kinetic_law_only = kwargs["parameters_in_kinetic_law_only"]
        non_constant_params = kwargs["non_constant_params"]
        if len(non_constant_params) > 0:
            non_constant_params = ",".join(non_constant_params)
            self.results.add_message(
                reaction_id, 1006, f"Expecting these parameters to be constants: {non_constant_params}")

    def _check_irreversibility(self, **kwargs):
        """
        Checks if an irreversible reaction's kinetic law contains products.
        Code: 1010

        Args:
            reaction_id (str): The reaction's id'.
            is_reversible (bool): the reaction's reversibility
            species_in_kinetic_law: A list of species present in the rate law.
            product_list: A list of products for the reaction.

        Returns:
            An error message specifying the products found in the rate law of an irreversible reaction.
        """
        reaction_id = kwargs["reaction_id"]
        is_reversible = kwargs["is_reversible"]
        species_in_kinetic_law = kwargs["species_in_kinetic_law"]
        product_list = kwargs["product_list"]

        inconsistent_products = []
        if not is_reversible:
            for product in product_list:
                if product in species_in_kinetic_law:
                    inconsistent_products.append(product)
        if len(inconsistent_products) > 0:
            inconsistent_products = ",".join(inconsistent_products)
            self.results.add_message(
                reaction_id, 1010, f"Irreversible reaction kinetic law contains products: {inconsistent_products}")

    def _check_naming_conventions(self, **kwargs):
        """
        Checks if certain parameters in the rate law follow the recommended naming convention (starting with 'k', 'K', or 'V').
        Code: 1020, 1021, 1022

        Args:
            reaction_id (str): The reaction's id'.

        Adds:
            A warning message to results specifying that certain parameters in the rate law are not following the recommended naming convention.
        """
        reaction_id = kwargs["reaction_id"]
        parameters_in_kinetic_law = kwargs["parameters_in_kinetic_law"]
        kinetics_sim = kwargs["kinetics_sim"]
        ids_list = kwargs["ids_list"]
        codes = kwargs["codes"]

        naming_convention_warnings = {'k': [], 'K': [], 'V': []}
        if any(self.default_classifications[reaction_id][key] for key in NON_MM_KEYS):
            naming_convention_warnings['k'] = self._check_symbols_start_with(
                'k', parameters_in_kinetic_law)
        elif self.default_classifications[reaction_id]['MM']:
            eq = self._numerator_denominator(kinetics_sim, ids_list)
            eq0 = [param for param in parameters_in_kinetic_law if param in eq[0]]
            eq1 = [param for param in parameters_in_kinetic_law if param in eq[1]]
            naming_convention_warnings['V'] = self._check_symbols_start_with(
                'V', eq0)
            naming_convention_warnings['K'] = self._check_symbols_start_with(
                'K', eq1)
        elif self.default_classifications[reaction_id]['MMcat']:
            eq = self._numerator_denominator(kinetics_sim, ids_list)
            eq0 = [param for param in parameters_in_kinetic_law if param in eq[0]]
            eq1 = [param for param in parameters_in_kinetic_law if param in eq[1]]
            naming_convention_warnings['K'] = self._check_symbols_start_with('K', eq0)
            naming_convention_warnings['K'] = self._check_symbols_start_with('K', eq1)
        elif self.default_classifications[reaction_id]['Hill']:
            eq = self._numerator_denominator(kinetics_sim, ids_list)
            eq0 = [param for param in parameters_in_kinetic_law if param in eq[0]]
            eq1 = [param for param in parameters_in_kinetic_law if param in eq[1]]
            naming_convention_warnings['K'] = self._check_symbols_start_with(
                'K', eq1)

        if 1020 in codes and len(naming_convention_warnings['k']) > 0:
            naming_convention_warnings_k = ",".join(
                naming_convention_warnings['k'])
            self.results.add_message(
                reaction_id, 1020, f"We recommend that these parameters start with 'k': {naming_convention_warnings_k}")
        if 1021 in codes and len(naming_convention_warnings['K']) > 0:
            naming_convention_warnings_K = ",".join(
                naming_convention_warnings['K'])
            self.results.add_message(
                reaction_id, 1021, f"We recommend that these parameters start with 'K': {naming_convention_warnings_K}")
        if 1022 in codes and len(naming_convention_warnings['V']) > 0:
            naming_convention_warnings_V = ",".join(
                naming_convention_warnings['V'])
            self.results.add_message(
                reaction_id, 1022, f"We recommend that these parameters start with 'V': {naming_convention_warnings_V}")

    def _check_symbols_start_with(self, start, symbols):
        ret = []
        for symbol in symbols:
            if not symbol.startswith(start):
                ret.append(symbol)
        return ret

    def _numerator_denominator(self, kinetics_sim, ids_list):
        """
        Get the numerator and denominator of a "fraction" function.

        Parameters
        ----    
        kinetics_sim: string-simplified kinetics
        ids_list: list-id list including all the ids in kinetics, reactants and products

        Returns
        -------
        Type - the numerator and the denominator of the fraction
        """

        strange_func = 0
        pre_symbols = ''
        for i in range(len(ids_list)):
            pre_symbols += ids_list[i]
            pre_symbols += ' '
        pre_symbols = pre_symbols[:-1]  # remove the space at the end
        pre_symbols_comma = pre_symbols.replace(" ", ",")
        stmt = "%s = sp.symbols('%s')" % (pre_symbols_comma, pre_symbols)
        try:  # sometimes there is "invalid syntax error"
            exec(stmt, globals())
        except:
            strange_func = 1

        try:  # check if there is strange func (i.e. delay) in kinetic law;
            # sometimes ids_list is not enough for all the ids in kinetics
            eq_stat = "kinetics_eq = " + kinetics_sim
            exec(eq_stat, globals())
        except:
            strange_func = 1

        eq = ['', '']

        if strange_func == 0:
            try:
                numerator = str(kinetics_eq.as_numer_denom()[0])
                denominator = str(kinetics_eq.as_numer_denom()[1])
                eq[0] = numerator
                eq[1] = denominator
            except:
                pass

        return eq

    def _numerator_denominator_order_remained(self, kinetics, ids_list):
        # Split the fraction at the '/' character
        split_fraction = kinetics.split('/')

        # Check if there's a numerator and a denominator
        if len(split_fraction) != 2:
            return ['', '']

        # Return the numerator and the denominator as a tuple
        return split_fraction[0].strip(), split_fraction[1].strip()

    def _find_positions_in_rate_law(self, element_list, rate_law):
        largest_position = -1
        smallest_position = sys.maxsize
        prev_position = -1
        increasing_flag = True

        for element in element_list:
            pattern = re.compile(rf"\b{re.escape(element)}\b")
            match = pattern.search(rate_law)
            if match:
                index = match.start()
                largest_position = max(index, largest_position)
                smallest_position = min(index, smallest_position)
                if index < prev_position:
                    increasing_flag = False
                prev_position = index
        return largest_position, smallest_position, increasing_flag

    def _check_product_of_terms_format(self, kinetics, compartment_in_kinetic_law, parameters_in_kinetic_law_only, sorted_species):
        comp_stats = self._find_positions_in_rate_law(
            compartment_in_kinetic_law, kinetics)
        param_stats = self._find_positions_in_rate_law(
            parameters_in_kinetic_law_only, kinetics)
        spec_stats = self._find_positions_in_rate_law(sorted_species, kinetics)
        is_formatted = (comp_stats[0] < param_stats[1] or param_stats[1] == sys.maxsize) and \
                       (param_stats[0] < spec_stats[1] or spec_stats[1] == sys.maxsize) and \
                       (comp_stats[0] < spec_stats[1]
                        or spec_stats[1] == sys.maxsize)
        increasing_flag = comp_stats[2] and param_stats[2] and spec_stats[2]
        if is_formatted:
            return 0 if increasing_flag else 1
        return 2

    def _check_expression_format(self, kinetics, compartment_in_kinetic_law, parameters_in_kinetic_law_only, sorted_species):
        compartment_in_kinetic_law.sort()
        parameters_in_kinetic_law_only.sort()
        product_of_terms = re.split(r"[+-]", kinetics)
        ret = 0
        for term in product_of_terms:
            format_status = self._check_product_of_terms_format(
                term, compartment_in_kinetic_law, parameters_in_kinetic_law_only, sorted_species)
            if format_status > ret:
                ret = format_status
        return ret

    def _check_formatting_conventions(self, **kwargs):
        reaction_id = kwargs["reaction_id"]
        compartment_in_kinetic_law = kwargs["compartment_in_kinetic_law"]
        kinetics = kwargs["kinetics"]
        ids_list = kwargs["ids_list"]
        parameters_in_kinetic_law_only = kwargs["parameters_in_kinetic_law_only"]
        codes = kwargs["codes"]
        sorted_species = kwargs["sorted_species"]

        flag = 0
        assert len(self.default_classifications[reaction_id]) > 0
        if any(self.default_classifications[reaction_id][key] for key in MM_KEYS):
            eq = self._numerator_denominator_order_remained(
                kinetics, ids_list)  # _numerator_denominator not provided
            flag = self._check_expression_format(
                eq[0], compartment_in_kinetic_law, parameters_in_kinetic_law_only, sorted_species)
            flag += 3 * self._check_expression_format(
                eq[1], compartment_in_kinetic_law, parameters_in_kinetic_law_only, sorted_species)
        else:
            flag = self._check_expression_format(
                kinetics, compartment_in_kinetic_law, parameters_in_kinetic_law_only, sorted_species)
        if flag == 1 and 1030 in codes:
            self.results.add_message(
                reaction_id, 1030, f"Elements of the same type are not ordered alphabetically")
        if flag == 2 and 1031 in codes:
            self.results.add_message(
                reaction_id, 1031, f"Formatting convention not followed (compartment before parameters before species)")
        # TODO: currently the default classification does not classify these as MM, so these checks are not performed
        if flag == 3 and 1032 in codes:
            self.results.add_message(
                reaction_id, 1032, f"Denominator not in alphabetical order")
        if flag == 4 and 1033 in codes:
            self.results.add_message(
                reaction_id, 1033, f"Numerator and denominator not in alphabetical order")
        if flag == 5 and 1034 in codes:
            self.results.add_message(
                reaction_id, 1034, f"Numerator convention not followed and denominator not in alphabetical order")
        # if flag == 6 and 1035 in codes:
        #     self.results.add_message(
        #         reaction_id, 1035, f"Denominator convention not followed")
        # if flag == 7 and 1036 in codes:
        #     self.results.add_message(
        #         reaction_id, 1036, f"Numerator not in alphabetical order and denominator convention not followed")
        # if flag == 8 and 1037 in codes:
        #     self.results.add_message(
        #         reaction_id, 1037, f"Numerator and denominator convention not followed")

    def _check_sboterm_annotations(self, **kwargs):
        """
        Checks if the SBOTerm annotations for the rate law follow recommended SBO terms.
        Code: 1040, 1041, 1042, 1043, 1044

        Args:
            reaction_id (str): The reaction's id'.
            sbo_term (int): the sbo_term annotation for the kinetic law, -1 if not annotated

        Adds:
            A warning message to results specifying that the annotations for the rate law do not follow recommended SBO terms.
        """
        reaction_id = kwargs["reaction_id"]
        sbo_term = kwargs["sbo_term"]
        codes = kwargs["codes"]
        assert len(self.default_classifications) > 0
        flag = 0
        if sbo_term < 0:
            flag = 0
        elif any(self.default_classifications[reaction_id][key] for key in UNDR_KEYS):
            if sbo_term not in UNDR_SBOS:
                flag = 1
        elif any(self.default_classifications[reaction_id][key] for key in UNDR_A_KEYS):
            if sbo_term not in UNDR_A_SBOS:
                flag = 2
        elif any(self.default_classifications[reaction_id][key] for key in BIDR_ALL_KEYS):
            if sbo_term not in BI_SBOS:
                flag = 3
        elif self.default_classifications[reaction_id]['MM']:
            if sbo_term not in MM_SBOS:
                flag = 4
        elif any(self.default_classifications[reaction_id][key] for key in MM_CAT_KEYS):
            if sbo_term not in MM_CAT_SBOS:
                flag = 5
        # elif self.default_classifications[reaction_id]['Hill']:
        #     if sbo_term not in HILL_SBOS:
        #         flag = 6
        if flag == 1 and 1040 in codes:
            self.results.add_message(
                reaction_id, 1040, f"Uni-directional mass action annotation not following recommended SBO terms, we recommend annotations to be subclasses of: SBO_0000430, SBO_0000041")
        elif flag == 2 and 1041 in codes:
            self.results.add_message(
                reaction_id, 1041, f"Uni-Directional Mass Action with an Activator annotation not following recommended SBO terms, we recommend annotations to be subclasses of: SBO_0000041")
        elif flag == 3 and 1042 in codes:
            self.results.add_message(
                reaction_id, 1042, f"Bi-directional mass action (with an Activator) annotation not following recommended SBO terms, we recommend annotations to be subclasses of: SBO_0000042")
        elif flag == 4 and 1043 in codes:
            self.results.add_message(
                reaction_id, 1043, f"Michaelis-Menten kinetics without an explicit enzyme annotation not following recommended SBO terms, we recommend annotations to be subclasses of: SBO_0000028")
        elif flag == 5 and 1044 in codes:
            self.results.add_message(
                reaction_id, 1044, f"Michaelis-Menten kinetics with an explicit enzyme annotation not following recommended SBO terms, we recommend annotations to be subclasses of: SBO_0000028, SBO_0000430")
