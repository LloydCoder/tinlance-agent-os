"""Catalog/team evaluation primitives."""
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class EvaluationMeasurement:
    metric:str;value:float;passed:bool
@dataclass(frozen=True,slots=True)
class CatalogEvaluation:
    case_id:str;measurements:tuple[EvaluationMeasurement,...]
    @property
    def passed(self)->bool:return all(m.passed for m in self.measurements)
def evaluate(case_id:str,expected:dict[str,float],actual:dict[str,float],tolerance:float=0.0)->CatalogEvaluation:
    ms=tuple(EvaluationMeasurement(k,float(actual.get(k,0)),k in actual and abs(actual[k]-v)<=tolerance) for k,v in expected.items())
    return CatalogEvaluation(case_id,ms)
