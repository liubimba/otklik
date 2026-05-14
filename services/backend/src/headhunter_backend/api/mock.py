from .schemas import Vacancy, SearchFilter, WriteRequest
from datetime import datetime

mock_vacancy: Vacancy = Vacancy(
    vacancy_id=1,
    name="Software Engineer",
    description="We are looking for a skilled software engineer.",
    salary=50000,
    company_id=1,
    company_name="Tech Corp",
    city="San Francisco",
    created_at=datetime.now(),
    updated_at=datetime.now(),
    link="https://example.com/vacancy/1",
)

search_filter = SearchFilter(text="software engineer")

write_request = WriteRequest(
    text="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
)
