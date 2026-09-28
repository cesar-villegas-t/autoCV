import { useEffect, useState, type FormEvent } from 'react';
import { Icon } from '../../components/Icon';
import { ApiRequestError, clearProfile, fetchProfile, saveProfile } from '../../lib/api';
import {
  describeMissing, emptyDatedItem, emptyEducation, emptyExperience, emptyLanguage, emptyLink, emptyProfile,
  type CandidateProfile, type DatedItem, type Education, type Experience, type LanguageEntry, type ProfileLink,
} from '../../lib/profile';
import { BlockList } from './BlockList';
import { DatesFieldset } from './DatesFieldset';
import { TagInput } from './TagInput';

const MAX_RELOCATIONS = 10, MAX_LINKS = 10, MAX_EXPERIENCE = 30, MAX_EDUCATION = 20;
const MAX_ACHIEVEMENTS = 30, MAX_PROJECTS = 30, MAX_LANGUAGES = 15;

function set<T, K extends keyof T>(setter: (value: T) => void, value: T, key: K, field: T[K]) {
  setter({ ...value, [key]: field });
}

export function ProfileEditor() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [profile, setProfile] = useState<CandidateProfile>(emptyProfile);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [savedAt, setSavedAt] = useState(0);
  const [confirmingClear, setConfirmingClear] = useState(false);

  useEffect(() => {
    let active = true;
    fetchProfile()
      .then(response => {
        if (!active) return;
        setProfile(response.profile);
        setUpdatedAt(response.updated_at);
        setMissing(response.missing);
      })
      .catch(caught => { if (active) setLoadError(caught instanceof Error ? caught.message : 'No se pudo cargar el perfil.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!savedAt) return;
    const timer = setTimeout(() => setSavedAt(0), 4000);
    return () => clearTimeout(timer);
  }, [savedAt]);

  function fieldError(path: string): string | undefined {
    return fieldErrors[path];
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setSaveError('');
    setFieldErrors({});
    try {
      const response = await saveProfile(profile);
      setProfile(response.profile);
      setUpdatedAt(response.updated_at);
      setMissing(response.missing);
      setSavedAt(Date.now());
    } catch (caught) {
      if (caught instanceof ApiRequestError) {
        setSaveError(caught.message);
        setFieldErrors(caught.fields);
      } else {
        setSaveError(caught instanceof Error ? caught.message : 'No se pudo guardar el perfil.');
      }
    } finally {
      setSaving(false);
    }
  }

  async function confirmClear() {
    setSaving(true);
    try {
      await clearProfile();
      setProfile(emptyProfile);
      setUpdatedAt(null);
      setMissing(['name', 'email', 'experience_or_education']);
      setFieldErrors({});
      setSaveError('');
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'No se pudo borrar el perfil.');
    } finally {
      setSaving(false);
      setConfirmingClear(false);
    }
  }

  if (loading) return <section className="profile-shell"><p role="status">Cargando tu perfil…</p></section>;
  if (loadError) return <section className="profile-shell"><p className="field-error" role="alert"><Icon name="alert" />{loadError}</p></section>;

  return <section className="profile-shell" aria-labelledby="profile-title">
    <div className="profile-heading">
      <div>
        <h1 id="profile-title">Tu perfil</h1>
        <p>La información que autoCV usa para adaptar tu CV a cada oferta.</p>
      </div>
      {missing.length > 0
        ? <p className="profile-status is-incomplete" role="status">Falta: {describeMissing(missing)}.</p>
        : <p className="profile-status is-complete" role="status"><Icon name="check" />Perfil completo</p>}
    </div>

    <form onSubmit={submit} aria-label="Editar perfil">
      <fieldset>
        <legend>Contacto</legend>
        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="p-first-name">Nombre</label>
            <input id="p-first-name" value={profile.first_name} maxLength={80}
              onChange={event => set(setProfile, profile, 'first_name', event.target.value)} />
            {fieldError('first_name') && <p className="field-error" role="alert">{fieldError('first_name')}</p>}
          </div>
          <div className="form-field">
            <label htmlFor="p-last-name">Apellidos</label>
            <input id="p-last-name" value={profile.last_name} maxLength={120}
              onChange={event => set(setProfile, profile, 'last_name', event.target.value)} />
            {fieldError('last_name') && <p className="field-error" role="alert">{fieldError('last_name')}</p>}
          </div>
          <div className="form-field">
            <label htmlFor="p-location">Ubicación principal</label>
            <input id="p-location" value={profile.location} maxLength={120} placeholder="Madrid, España"
              onChange={event => set(setProfile, profile, 'location', event.target.value)} />
            {fieldError('location') && <p className="field-error" role="alert">{fieldError('location')}</p>}
          </div>
          <div className="form-field">
            <label htmlFor="p-phone">Teléfono</label>
            <input id="p-phone" type="tel" value={profile.phone} maxLength={30} placeholder="+34 600 000 000"
              onChange={event => set(setProfile, profile, 'phone', event.target.value)} />
            {fieldError('phone') && <p className="field-error" role="alert">{fieldError('phone')}</p>}
          </div>
          <div className="form-field">
            <label htmlFor="p-email">Email</label>
            <input id="p-email" type="email" value={profile.email} maxLength={320}
              onChange={event => set(setProfile, profile, 'email', event.target.value)} />
            {fieldError('email') && <p className="field-error" role="alert">{fieldError('email')}</p>}
          </div>
          <div className="form-field">
            <label htmlFor="p-linkedin">LinkedIn</label>
            <input id="p-linkedin" type="url" value={profile.linkedin} maxLength={200} placeholder="https://linkedin.com/in/tu-usuario"
              onChange={event => set(setProfile, profile, 'linkedin', event.target.value)} />
            {fieldError('linkedin') && <p className="field-error" role="alert">{fieldError('linkedin')}</p>}
          </div>
        </div>
        <div className="form-field">
          <label htmlFor="p-relocations">Posibles relocations</label>
          <TagInput id="p-relocations" values={profile.relocations} max={MAX_RELOCATIONS}
            placeholder="Añade una ciudad y pulsa Enter" onChange={values => set(setProfile, profile, 'relocations', values)} />
          {fieldError('relocations') && <p className="field-error" role="alert">{fieldError('relocations')}</p>}
        </div>
      </fieldset>

      <fieldset>
        <legend>Otros enlaces</legend>
        <BlockList<ProfileLink> items={profile.links} max={MAX_LINKS} addLabel="Añadir enlace" empty={emptyLink}
          itemLabel={(link, index) => link.label || `Enlace ${index + 1}`}
          onChange={links => set(setProfile, profile, 'links', links)}>
          {(link, update, index) => <div className="form-grid">
            <div className="form-field">
              <label htmlFor={`p-link-label-${index}`}>Nombre</label>
              <input id={`p-link-label-${index}`} value={link.label} maxLength={60} placeholder="GitHub"
                onChange={event => update({ label: event.target.value })} />
              {fieldError(`links.${index}.label`) && <p className="field-error" role="alert">{fieldError(`links.${index}.label`)}</p>}
            </div>
            <div className="form-field">
              <label htmlFor={`p-link-url-${index}`}>Enlace</label>
              <input id={`p-link-url-${index}`} type="url" value={link.url} maxLength={200} placeholder="https://github.com/tu-usuario"
                onChange={event => update({ url: event.target.value })} />
              {fieldError(`links.${index}.url`) && <p className="field-error" role="alert">{fieldError(`links.${index}.url`)}</p>}
            </div>
          </div>}
        </BlockList>
      </fieldset>

      <fieldset>
        <legend>Resumen profesional</legend>
        <div className="form-field">
          <label htmlFor="p-summary">Un resumen breve de tu perfil</label>
          <textarea id="p-summary" rows={3} maxLength={2000} value={profile.summary}
            onChange={event => set(setProfile, profile, 'summary', event.target.value)} />
          {fieldError('summary') && <p className="field-error" role="alert">{fieldError('summary')}</p>}
        </div>
      </fieldset>

      <fieldset>
        <legend>Work Experience</legend>
        <BlockList<Experience> items={profile.experience} max={MAX_EXPERIENCE} addLabel="Añadir experiencia" empty={emptyExperience}
          itemLabel={(job, index) => job.title && job.company ? `${job.title} · ${job.company}` : `Experiencia ${index + 1}`}
          onChange={experience => set(setProfile, profile, 'experience', experience)}>
          {(job, update, index) => <>
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor={`p-exp-company-${index}`}>Empresa</label>
                <input id={`p-exp-company-${index}`} value={job.company} maxLength={120} onChange={event => update({ company: event.target.value })} />
                {fieldError(`experience.${index}.company`) && <p className="field-error" role="alert">{fieldError(`experience.${index}.company`)}</p>}
              </div>
              <div className="form-field">
                <label htmlFor={`p-exp-title-${index}`}>Puesto</label>
                <input id={`p-exp-title-${index}`} value={job.title} maxLength={120} onChange={event => update({ title: event.target.value })} />
                {fieldError(`experience.${index}.title`) && <p className="field-error" role="alert">{fieldError(`experience.${index}.title`)}</p>}
              </div>
            </div>
            <DatesFieldset start={job.start_date} end={job.end_date} current={job.current} startRequired currentLabel="Actualmente en este puesto"
              onChange={patch => update({
                ...(patch.start_date !== undefined ? { start_date: patch.start_date ?? '' } : {}),
                ...(patch.end_date !== undefined ? { end_date: patch.end_date } : {}),
                ...(patch.current !== undefined ? { current: patch.current } : {}),
              })}
              error={field => fieldError(`experience.${index}.${field}`) ?? (field === 'end_date' ? fieldError(`experience.${index}`) : undefined)} />
            <div className="form-field">
              <label htmlFor={`p-exp-desc-${index}`}>Descripción / más info</label>
              <textarea id={`p-exp-desc-${index}`} rows={3} maxLength={4000} placeholder="Una línea por logro"
                value={job.description} onChange={event => update({ description: event.target.value })} />
              {fieldError(`experience.${index}.description`) && <p className="field-error" role="alert">{fieldError(`experience.${index}.description`)}</p>}
            </div>
          </>}
        </BlockList>
      </fieldset>

      <fieldset>
        <legend>Educación</legend>
        <BlockList<Education> items={profile.education} max={MAX_EDUCATION} addLabel="Añadir formación" empty={emptyEducation}
          itemLabel={(item, index) => item.degree || `Formación ${index + 1}`}
          onChange={education => set(setProfile, profile, 'education', education)}>
          {(item, update, index) => <>
            <div className="form-grid">
              <div className="form-field">
                <label htmlFor={`p-edu-school-${index}`}>Escuela/Universidad</label>
                <input id={`p-edu-school-${index}`} value={item.institution} maxLength={160} onChange={event => update({ institution: event.target.value })} />
                {fieldError(`education.${index}.institution`) && <p className="field-error" role="alert">{fieldError(`education.${index}.institution`)}</p>}
              </div>
              <div className="form-field">
                <label htmlFor={`p-edu-degree-${index}`}>Titulación</label>
                <input id={`p-edu-degree-${index}`} value={item.degree} maxLength={160} onChange={event => update({ degree: event.target.value })} />
                {fieldError(`education.${index}.degree`) && <p className="field-error" role="alert">{fieldError(`education.${index}.degree`)}</p>}
              </div>
              <div className="form-field">
                <label htmlFor={`p-edu-location-${index}`}>Ubicación</label>
                <input id={`p-edu-location-${index}`} value={item.location} maxLength={120} onChange={event => update({ location: event.target.value })} />
              </div>
              <div className="form-field">
                <label htmlFor={`p-edu-grade-${index}`}>Calificación obtenida</label>
                <input id={`p-edu-grade-${index}`} value={item.grade} maxLength={60} placeholder="8.1 / 10" onChange={event => update({ grade: event.target.value })} />
              </div>
            </div>
            <DatesFieldset start={item.start_date} end={item.end_date} current={item.current} currentLabel="En curso"
              onChange={patch => update(patch)}
              error={field => fieldError(`education.${index}.${field}`) ?? (field === 'end_date' ? fieldError(`education.${index}`) : undefined)} />
            <div className="form-field">
              <label htmlFor={`p-edu-desc-${index}`}>Descripción / más info</label>
              <textarea id={`p-edu-desc-${index}`} rows={2} maxLength={4000} value={item.description} onChange={event => update({ description: event.target.value })} />
            </div>
          </>}
        </BlockList>
      </fieldset>

      <DatedItemSection legend="Logros" addLabel="Añadir logro" max={MAX_ACHIEVEMENTS}
        items={profile.achievements} onChange={achievements => set(setProfile, profile, 'achievements', achievements)}
        fieldError={fieldError} pathPrefix="achievements" namePlaceholder="Premio, reconocimiento…" />

      <DatedItemSection legend="Proyectos" addLabel="Añadir proyecto" max={MAX_PROJECTS}
        items={profile.projects} onChange={projects => set(setProfile, profile, 'projects', projects)}
        fieldError={fieldError} pathPrefix="projects" namePlaceholder="Nombre del proyecto" />

      <fieldset>
        <legend>Skills</legend>
        <div className="form-field">
          <label htmlFor="p-skills">Añade todas las skills y conocimientos que consideres oportunos</label>
          <textarea id="p-skills" rows={4} maxLength={6000} value={profile.skills}
            onChange={event => set(setProfile, profile, 'skills', event.target.value)} />
          {fieldError('skills') && <p className="field-error" role="alert">{fieldError('skills')}</p>}
        </div>
      </fieldset>

      <fieldset>
        <legend>Idiomas</legend>
        <BlockList<LanguageEntry> items={profile.languages} max={MAX_LANGUAGES} addLabel="Añadir idioma" empty={emptyLanguage}
          itemLabel={(item, index) => item.language || `Idioma ${index + 1}`}
          onChange={languages => set(setProfile, profile, 'languages', languages)}>
          {(item, update, index) => <div className="form-grid">
            <div className="form-field">
              <label htmlFor={`p-lang-name-${index}`}>Idioma</label>
              <input id={`p-lang-name-${index}`} value={item.language} maxLength={60} onChange={event => update({ language: event.target.value })} />
              {fieldError(`languages.${index}.language`) && <p className="field-error" role="alert">{fieldError(`languages.${index}.language`)}</p>}
            </div>
            <div className="form-field">
              <label htmlFor={`p-lang-level-${index}`}>Nivel</label>
              <input id={`p-lang-level-${index}`} list="language-levels" value={item.level} maxLength={60}
                placeholder="B2, C1, Nativo…" onChange={event => update({ level: event.target.value })} />
            </div>
            <div className="form-field">
              <label htmlFor={`p-lang-cert-${index}`}>Certificación</label>
              <input id={`p-lang-cert-${index}`} value={item.certification} maxLength={120} placeholder="TOEFL 104"
                onChange={event => update({ certification: event.target.value })} />
            </div>
          </div>}
        </BlockList>
        <datalist id="language-levels">
          {['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Nativo'].map(level => <option value={level} key={level} />)}
        </datalist>
      </fieldset>

      {saveError && <p className="field-error" role="alert"><Icon name="alert" />{saveError}</p>}
      <div className="profile-actions">
        <div className="profile-save-status" role="status" aria-live="polite">
          {saving ? 'Guardando…' : savedAt > 0 ? 'Perfil guardado.'
            : updatedAt ? `Última actualización: ${new Date(updatedAt).toLocaleString('es-ES')}` : 'Perfil sin guardar todavía.'}
        </div>
        <div className="profile-actions-buttons">
          {confirmingClear
            ? <>
                <span>¿Borrar todo el perfil?</span>
                <button type="button" className="text-button" onClick={() => setConfirmingClear(false)}>Cancelar</button>
                <button type="button" className="danger-button" onClick={confirmClear} disabled={saving}>Sí, borrar</button>
              </>
            : <button type="button" className="text-button" onClick={() => setConfirmingClear(true)}>Borrar perfil</button>}
          <button className="primary-button" type="submit" disabled={saving} aria-busy={saving}>
            {saving ? 'Guardando…' : 'Guardar perfil'}
          </button>
        </div>
      </div>
    </form>
  </section>;
}

function DatedItemSection({ items, onChange, max, legend, addLabel, fieldError, pathPrefix, namePlaceholder }: {
  items: DatedItem[]; onChange: (items: DatedItem[]) => void; max: number; legend: string;
  addLabel: string; fieldError: (path: string) => string | undefined; pathPrefix: string; namePlaceholder: string;
}) {
  return <fieldset>
    <legend>{legend}</legend>
    <BlockList<DatedItem> items={items} max={max} addLabel={addLabel} empty={emptyDatedItem}
      itemLabel={(item, index) => item.name || `${legend.slice(0, -1)} ${index + 1}`} onChange={onChange}>
      {(item, update, index) => <>
        <div className="form-field">
          <label htmlFor={`p-${pathPrefix}-name-${index}`}>Nombre</label>
          <input id={`p-${pathPrefix}-name-${index}`} value={item.name} maxLength={160} placeholder={namePlaceholder}
            onChange={event => update({ name: event.target.value })} />
          {fieldError(`${pathPrefix}.${index}.name`) && <p className="field-error" role="alert">{fieldError(`${pathPrefix}.${index}.name`)}</p>}
        </div>
        <DatesFieldset start={item.start_date} end={item.end_date} current={item.current}
          onChange={patch => update(patch)}
          error={field => fieldError(`${pathPrefix}.${index}.${field}`) ?? (field === 'end_date' ? fieldError(`${pathPrefix}.${index}`) : undefined)} />
        <div className="form-field">
          <label htmlFor={`p-${pathPrefix}-desc-${index}`}>Descripción / más info</label>
          <textarea id={`p-${pathPrefix}-desc-${index}`} rows={2} maxLength={4000} value={item.description}
            onChange={event => update({ description: event.target.value })} />
        </div>
      </>}
    </BlockList>
  </fieldset>;
}
