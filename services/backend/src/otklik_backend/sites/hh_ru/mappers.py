from otklik_backend.api.schemas import WorkFormat, EmploymentType


class HHRUWorkFormatMapper:
    def __init__(self) -> None:
        pass

    def from_raw(self, raw_str: str | None) -> list[WorkFormat]:
        if raw_str is None:
            return [WorkFormat.UNKNOWN]
        raw_str = raw_str.strip().lower().replace("\xa0", " ")
        types: list[WorkFormat] = []
        if "удаленная работа" in raw_str:
            types.append(WorkFormat.REMOTE)
        if "гибридный формат" in raw_str:
            types.append(WorkFormat.HYBRID)
        if "на месте" in raw_str:
            types.append(WorkFormat.ONSITE)
        if "разъездной" in raw_str:
            types.append(WorkFormat.TRAVELING)
        return types


class HHRUEmploymentTypeMapper:
    def __init__(self) -> None:
        pass

    def from_raw(self, raw_str: str | None) -> list[EmploymentType]:
        if raw_str is None:
            return [EmploymentType.UNKNOWN]
        raw_str = raw_str.strip().lower().replace("\xa0", " ")
        types: list[EmploymentType] = []
        if "полная занятость" in raw_str:
            types.append(EmploymentType.FULL_TIME)
        if "вахта" in raw_str:
            types.append(EmploymentType.ROTATIONAL)
        if "частичная занятость" in raw_str:
            types.append(EmploymentType.PART_TIME)
        if "подработка" in raw_str:
            types.append(EmploymentType.SIDE_JOB)
        if "оформление по гпх или по совместительству" in raw_str:
            types.append(EmploymentType.CONTRACT)
        if "стажировка" in raw_str:
            types.append(EmploymentType.INTERNSHIP)
        return types
