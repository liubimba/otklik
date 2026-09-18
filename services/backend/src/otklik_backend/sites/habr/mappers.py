from otklik_backend.api.schemas import EmploymentType, WorkFormat


class HabrWorkFormatMapper:
    def from_raw(self, raw_str: str | None) -> list[WorkFormat]:
        if raw_str is None:
            return [WorkFormat.UNKNOWN]
        text = raw_str.strip().lower().replace("\xa0", " ")
        formats: list[WorkFormat] = []
        if "гибрид" in text:
            formats.append(WorkFormat.HYBRID)
        if "удал" in text or "удалённо" in text or "удаленно" in text:
            formats.append(WorkFormat.REMOTE)
        if "офис" in text:
            formats.append(WorkFormat.ONSITE)
        return formats or [WorkFormat.UNKNOWN]


class HabrEmploymentTypeMapper:
    def from_raw(self, raw_str: str | None) -> list[EmploymentType]:
        if raw_str is None:
            return [EmploymentType.UNKNOWN]
        text = raw_str.strip().lower().replace("\xa0", " ")
        part_time = "неполный рабочий день" in text or "частичн" in text
        types: list[EmploymentType] = []
        if part_time:
            types.append(EmploymentType.PART_TIME)
        if "полный рабочий день" in text and not part_time:
            types.append(EmploymentType.FULL_TIME)
        if "стажировк" in text:
            types.append(EmploymentType.INTERNSHIP)
        return types or [EmploymentType.UNKNOWN]
