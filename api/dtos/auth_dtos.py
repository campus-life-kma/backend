import re
from dataclasses import dataclass


@dataclass
class MicrosoftUserDTO:
    email: str
    display_name: str
    job_title: str

    @classmethod
    def from_json(cls, json_data: dict) -> "MicrosoftUserDTO":
        email = json_data.get("mail") or json_data.get("userPrincipalName", "")
        return cls(
            email=email.lower(), display_name=json_data.get("displayName", ""), job_title=json_data.get("jobTitle", "")
        )

    @property
    def is_valid_email(self) -> bool:
        return self.email.endswith("@ukma.edu.ua")

    def get_parsed_academic_info(self) -> tuple[str | None, int | None]:
        if not self.job_title:
            return None, None

        admission_year = None
        major_name = None

        year_match = re.search(r"\b(\d{4})\b", self.job_title)
        if year_match:
            admission_year = int(year_match.group(1))

        if admission_year:
            name_match = re.search(rf"\.\s*(.*?)\s*{admission_year}", self.job_title)
            if name_match:
                major_name = name_match.group(1).strip()
        else:
            name_match = re.search(r"\.\s*(.*)", self.job_title)
            if name_match:
                parts = name_match.group(1).strip().rsplit(" ", 1)
                major_name = parts[0] if len(parts) > 1 else name_match.group(1).strip()

        return major_name, admission_year
