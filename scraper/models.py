from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobPosting:
    company: str
    industry: str
    platform: str
    title: str
    department: str
    location: str
    description: str
    link: str
    posted_date: Optional[str] = field(default=None)  # ISO date string or None

    def to_dict(self) -> dict:
        return {
            "company":     self.company,
            "industry":    self.industry,
            "platform":    self.platform,
            "title":       self.title,
            "department":  self.department,
            "location":    self.location,
            "description": self.description,
            "link":        self.link,
            "posted_date": self.posted_date,
        }
