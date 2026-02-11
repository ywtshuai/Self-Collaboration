import ast
import json
from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class InstanceData:
    instance_id: str
    problem_statement: str
    starter_code: str
    test_cases: Dict[str, List[Any]]
    solutions: List[str]


def load_data(data_name):
    test_data = []
    for temp in open(f"./Datasets/{data_name}.jsonl", 'r', encoding='utf-8').readlines():
        test_data.append(json.loads(temp))

    return test_data


def get_data(data_name: str) -> List[InstanceData]:
    data_list = []
    raw_data = load_data(data_name)
    for data in raw_data:
        if data_name == 'apps':
            instance = InstanceData(
                instance_id=data['problem_id'],
                problem_statement=data['question'],
                starter_code=data['starter_code'],
                test_cases=data['all_test_cases'],
                solutions=ast.literal_eval(data['solutions']) if data['solutions'] else []
            )
        elif data_name == 'code_contests':
            filtered_solutions = {'language': [], 'solution': []}
            for language, solution in zip(data['solutions']['language'], data['solutions']['solution']):
                if language == 3:
                    filtered_solutions['language'].append(language)
                    filtered_solutions['solution'].append(solution)
            data['solutions'] = filtered_solutions

            instance = InstanceData(
                instance_id=data['problem_id'],
                problem_statement=data['description'],
                starter_code='',
                test_cases=data['all_test_cases'],
                solutions=data['solutions']['solution']
            )
        else:
            raise ValueError(f"Unsupported data_name: {data_name}")
        data_list.append(instance)
    return data_list
