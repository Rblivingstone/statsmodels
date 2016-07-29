import re
import os

import numpy as np

debug_mode = False


def print_debug_output(results, dt):
        print("\n\n\nDETERMINISTIC TERMS: " + dt)
        alpha = results["est"]["alpha"]
        print("alpha:")
        print(str(type(alpha)) + str(alpha.shape))
        print(alpha)
        print("se: ")
        print(results["se"]["alpha"])
        print("t: ")
        print(results["t"]["alpha"])
        print("p: ")
        print(results["p"]["alpha"])
        beta = results["est"]["beta"]
        print("beta:")
        print(str(type(beta)) + str(beta.shape))
        print(beta)
        Gamma = results["est"]["Gamma"]
        print("Gamma:")
        print(str(type(Gamma)) + str(Gamma.shape))
        print(Gamma)
        if "co" in dt or "s" in dt or "lo" in dt:
            C = results["est"]["C"]
            print("C:")
            print(str(type(C)) + str(C.shape))
            print(C)
            print("se: ")
            print(results["se"]["C"])


def dt_s_tup_to_string(dt_s_tup):
    dt_string = dt_s_tup[0]  # string for identifying the file to parse.
    if dt_s_tup[1] > 0:  # if there are seasons in the model
        if "co" in dt_string or "ci" in dt_string or "nc" in dt_string:
            dt_string = dt_string[:2] + "s" + dt_string[2:]
        else:
            dt_string = "s" + dt_string
    return dt_string


def load_results_jmulti(dataset, dt_s_list):
    """

    Parameters
    ----------
    dataset : module
        A data module in the statsmodels/datasets directory that defines a
        __str__() method returning the dataset's name.
    dt_s_list : list
        A list of strings where each string represents a combination of
        deterministic terms.

    Returns
    -------
    result : dict
        A dict (keys: tuples of deterministic terms and seasonal terms)
        of dicts (keys: strings "est" (for estimators),
                              "se" (for standard errors),
                              "t" (for t-values),
                              "p" (for p-values))
        of dicts (keys: strings "alpha", "beta", "Gamma" and other results)
    """
    source = "jmulti"

    results_dict_per_det_terms = dict.fromkeys(dt_s_list)
        
    for dt_s in dt_s_list:
        dt_string = dt_s_tup_to_string(dt_s)
        params_file = dataset.__str__()+"_"+source+"_"+dt_string+".txt"
        params_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   params_file)
        # sections in jmulti output:
        section_header = ["Lagged endogenous term",  # Gamma
                          "Deterministic term",      # co, s, lo
                          "Loading coefficients",    # alpha
                          "Estimated cointegration relation",  # beta
                          "Legend",
                          "Lagged endogenous term",  # VAR representation
                          "Deterministic term"]      # VAR representation
        # the following "sections" will serve as key for the corresponding
        # result values
        sections = ["Gamma",
                    "C",     # Here all deterministic term coefficients are
                             # collected. (const and linear trend which belong
                             # to cointegration relation as well as seasonal
                             # components which are outside the cointegration
                             # relation. Later, we will strip the terms related
                             # to the cointegration relation from C.
                    "alpha",
                    "beta",
                    "Legend",
                    "VAR A",  # VAR parameter matrices
                    "VAR deterministic"]  # VAR deterministic terms
        if "co" not in dt_string and "lo" not in dt_string \
                and "s" not in dt_string:
            # JMulTi: no deterministic terms section in VEC representation
            del(section_header[1])
            del(sections[1])
            if "ci" not in dt_string and "li" not in dt_string:
                # JMulTi: no deterministic section in VAR repr.
                del(section_header[-1])
                del(sections[-1])
        results = dict()
        results["est"] = dict.fromkeys(sections)
        results["se"] = dict.fromkeys(sections)
        results["t"] = dict.fromkeys(sections)
        results["p"] = dict.fromkeys(sections)
        section = -1
        result = []
        result_se = []
        result_t = []
        result_p = []

        rows = 0
        started_reading_section = False
        start_end_mark = "-----"
        # parse information about \alpha, \beta, \Gamma, deterministic of VECM
        # and A_i and deterministic of corresponding VAR:
        for line in open(params_file):
            if section == -1 and section_header[section+1] not in line:
                continue
            if section < len(section_header)-1 \
                    and section_header[section+1] in line:  # new section
                section += 1
                continue
            if not started_reading_section:
                if line.startswith(start_end_mark):
                    started_reading_section = True
                continue
            if started_reading_section:
                if line.startswith(start_end_mark):
                    if result == []:  # no values collected in section "Legend"
                        started_reading_section = False
                        continue
                    results["est"][sections[section]] = np.column_stack(
                                                                    result)
                    result = []
                    results["se"][sections[section]] = np.column_stack(
                                                                    result_se)
                    result_se = []
                    results["t"][sections[section]] = np.column_stack(
                                                                    result_t)
                    result_t = []
                    results["p"][sections[section]] = np.column_stack(
                                                                    result_p)
                    result_p = []
                    started_reading_section = False
                    continue
                str_number = "-?\d+\.\d{3}"
                regex_est = re.compile(str_number + "[^\)\]\}]")
                est_col = re.findall(regex_est, line)
                # standard errors in parantheses in JMulTi output:
                regex_se = re.compile("\(" + str_number + "\)")
                se_col = re.findall(regex_se, line)
                # t-values in brackets in JMulTi output:
                regex_t_value = re.compile("\[" + str_number + "\]")
                t_col = re.findall(regex_t_value, line)
                # p-values in braces in JMulTi output:
                regex_p_value = re.compile("\{" + str_number + "\}")
                p_col = re.findall(regex_p_value, line)
                if result == [] and est_col != []:
                    rows = len(est_col)
                if est_col != []:
                    est_col = [float(el) for el in est_col]
                    result.append(est_col)
                elif se_col != []:
                    for i in range(rows):
                        se_col[i] = se_col[i].replace("(", "").replace(")", "")
                    se_col = [float(el) for el in se_col]
                    result_se.append(se_col)
                elif t_col != []:
                    for i in range(rows):
                        t_col[i] = t_col[i].replace("[", "").replace("]", "")
                    t_col = [float(el) for el in t_col]
                    result_t.append(t_col)
                elif p_col != []:
                    for i in range(rows):
                        p_col[i] = p_col[i].replace("{", "").replace("}", "")
                    p_col = [float(el) for el in p_col]
                    result_p.append(p_col)
        # delete "Legend"-section of JMulTi:
        del results["est"]["Legend"]
        del results["se"]["Legend"]
        del results["t"]["Legend"]
        del results["p"]["Legend"]
        # JMulTi outputs beta.T
        results["est"]["beta"] = results["est"]["beta"].T
        results["se"]["beta"] = results["se"]["beta"].T
        results["t"]["beta"] = results["t"]["beta"].T
        results["p"]["beta"] = results["p"]["beta"].T
        # split information about beta and deterministic terms inside coint.
        alpha = results["est"]["alpha"]
        beta = results["est"]["beta"]
        alpha_rows = alpha.shape[0]
        if beta.shape[0] > alpha_rows:
            results["est"]["beta"], results["est"]["det_coint"] = np.vsplit(
                results["est"]["beta"], [alpha_rows])
            results["se"]["beta"], results["se"]["det_coint"] = np.vsplit(
                results["se"]["beta"], [alpha_rows])
            results["t"]["beta"], results["t"]["det_coint"] = np.vsplit(
                results["t"]["beta"], [alpha_rows])
            results["p"]["beta"], results["p"]["det_coint"] = np.vsplit(
                results["p"]["beta"], [alpha_rows])

        # parse information regarding \Sigma_u
        sigmau_file = dataset.__str__() + "_" + source + "_" + dt_string \
            + "_Sigmau" + ".txt"
        sigmau_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   sigmau_file)
        rows_to_parse = 0
        # all numbers of Sigma_u in notation with e (e.g. 2.283862e-05)
        regex_est = re.compile("\s+\S+e\S+")
        sigmau_section_reached = False
        for line in open(sigmau_file):
            if line.startswith("Log Likelihood:"):
                line = line.split("Log Likelihood:")[1]
                results["log_like"] = float(re.findall(regex_est, line)[0])
            if not sigmau_section_reached and "Covariance:" not in line:
                continue
            if "Covariance:" in line:
                sigmau_section_reached = True
                row = re.findall(regex_est, line)
                rows_to_parse = len(row)  # Sigma_u quadratic ==> #rows==#cols
                Sigma_u = np.empty((rows_to_parse, rows_to_parse))
            row = re.findall(regex_est, line)
            rows_to_parse -= 1
            Sigma_u[rows_to_parse] = row  # rows are added in reverse order
            if rows_to_parse == 0:
                break
        results["est"]["Sigma_u"] = Sigma_u[::-1]

        # parse forecast related outputs
        fc_file = dataset.__str__() + "_" + source + "_" + dt_string \
            + "_fc5" + ".txt"
        fc_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   fc_file)
        fc, lower, upper, plu_min = [], [], [], []
        for line in open(fc_file, encoding='latin_1'):

            str_number = "(\s+-?\d+\.\d{3}\s*)"
            regex_number = re.compile(str_number)
            numbers = re.findall(regex_number, line)
            if numbers == []:
                continue
            fc.append(float(numbers[0]))
            lower.append(float(numbers[1]))
            upper.append(float(numbers[2]))
            plu_min.append(float(numbers[3]))
        variables = alpha.shape[0]
        fc = np.hstack(np.vsplit(np.array(fc)[:, None], variables))
        lower = np.hstack(np.vsplit(np.array(lower)[:, None], variables))
        upper = np.hstack(np.vsplit(np.array(upper)[:, None], variables))
        plu_min = np.hstack(np.vsplit(np.array(plu_min)[:, None], variables))
        results["fc"] = dict.fromkeys(["fc", "lower", "upper"])
        results["fc"]["fc"] = fc
        results["fc"]["lower"] = lower
        results["fc"]["upper"] = upper

        if debug_mode:
            print_debug_output(results, dt_string)

        results_dict_per_det_terms[dt_s] = results

    return results_dict_per_det_terms
