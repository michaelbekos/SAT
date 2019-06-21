import subprocess

from werkzeug.exceptions import HTTPException, BadRequest

from be.custom_types import SolverResult
from be.exceptions import IdRelatedException
from be.model import SatModel
from be.utils import CodeTimer


class SolverInterface(object):
    @classmethod
    def solve(cls, nodes, edges, pages, constraints, entity_id) -> SolverResult:
        try:
            with CodeTimer("solve.SAT"):
                with CodeTimer("solve.SAT.var_creation"):
                    model = SatModel(pages, edges, nodes, constraints)

                    model.add_relative_node_order_clauses()

                    model.add_page_assignment_clauses()

                with CodeTimer("solve.SAT.page_constraints"):
                    model.add_page_type_constraints()

                with CodeTimer("solve.SAT.additional_constraints"):
                    model.add_constraints()

            with CodeTimer("solve.to_dimacs"):
                dimacstr = model.to_dimacs_str()
            with CodeTimer("solve.to_lingeline_and_back"):
                output = cls.call_lingeling_with_string(dimacstr)

                sat_result = model.parse_linegeling_result(str(output, encoding='UTF-8'))

                page_assignments = None
                vertex_order = None
                if sat_result['satisfiable']:
                    vertex_order = model.get_vertex_order()
                    page_assignments = model.get_page_assignments()

            return SolverResult(satisfiable=sat_result['satisfiable'],
                                page_assignments=page_assignments,
                                vertex_order=vertex_order,
                                solver_output=sat_result['full'],
                                entity_id=entity_id)
        except KeyError as e:
            raise BadRequest("The id {} was not found in the graph".format(str(e))) from e
        except HTTPException as e:
            raise e
        except Exception as e:
            raise IdRelatedException(entity_id, "{} : {} ".format(type(e), str(e))) from e

    @classmethod
    def call_lingeling_with_string(cls, dimacstr):
        try:
            output = subprocess.check_output(["lingeling"], input=bytes(dimacstr, 'UTF-8'))
        except subprocess.CalledProcessError as e:
            # lingeling does return 10 as returncode if everything is alright
            if e.returncode == 10 or e.returncode == 20:
                output = e.output
            elif e.returncode == 1:
                raise Exception("The dimacs file was incorrect and was rejected from lingeling. "
                                "The file was {}".format(dimacstr)) from e
            else:
                raise Exception(
                    "lingeling call failed with stderr >{}< and stdout >{}<".format(e.stderr, e.stdout)) from e
        return output