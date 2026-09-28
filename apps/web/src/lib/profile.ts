// Mirrors autocv.domain.profile.CandidateProfile (src/autocv/domain/profile.py).
export interface ProfileLink { label: string; url: string }
export interface Experience {
  company: string; title: string; start_date: string; end_date: string | null;
  current: boolean; description: string;
}
export interface Education {
  institution: string; degree: string; location: string;
  start_date: string | null; end_date: string | null; current: boolean;
  grade: string; description: string;
}
export interface DatedItem {
  name: string; start_date: string | null; end_date: string | null;
  current: boolean; description: string;
}
export interface LanguageEntry { language: string; level: string; certification: string }

export interface CandidateProfile {
  first_name: string; last_name: string; location: string; relocations: string[];
  phone: string; email: string; linkedin: string; links: ProfileLink[];
  summary: string; experience: Experience[]; education: Education[];
  achievements: DatedItem[]; projects: DatedItem[]; skills: string; languages: LanguageEntry[];
}

export interface ProfileResponse {
  profile: CandidateProfile;
  updated_at: string | null;
  missing: string[];
  complete: boolean;
}

export const emptyProfile: CandidateProfile = {
  first_name: '', last_name: '', location: '', relocations: [],
  phone: '', email: '', linkedin: '', links: [],
  summary: '', experience: [], education: [], achievements: [], projects: [],
  skills: '', languages: [],
};

export const emptyLink: ProfileLink = { label: '', url: '' };
export const emptyExperience: Experience = {
  company: '', title: '', start_date: '', end_date: null, current: false, description: '',
};
export const emptyEducation: Education = {
  institution: '', degree: '', location: '', start_date: null, end_date: null,
  current: false, grade: '', description: '',
};
export const emptyDatedItem: DatedItem = {
  name: '', start_date: null, end_date: null, current: false, description: '',
};
export const emptyLanguage: LanguageEntry = { language: '', level: '', certification: '' };

const MISSING_LABELS: Record<string, string> = {
  name: 'el nombre', email: 'el email',
  experience_or_education: 'al menos una experiencia o formación',
};

export function describeMissing(missing: string[]): string {
  return missing.map(key => MISSING_LABELS[key] ?? key).join(', ');
}
