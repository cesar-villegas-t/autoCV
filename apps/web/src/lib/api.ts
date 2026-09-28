import { emptyProfile, type CandidateProfile, type ProfileResponse } from './profile';

export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export type GenerationStatus = 'pending' | 'generating' | 'completed' | 'failed';
export interface GenerateRequest {
  profile_text?: string;
  use_saved_profile?: boolean;
  offer_text: string;
  output_name?: string;
}
export interface ApiError { code: string; message: string }
export interface GenerationResponse {
  id: string;
  status: GenerationStatus;
  download_url: string | null;
  error: ApiError | null;
}
export interface AuthUser { id: string; email: string; created_at: string }

const NETWORK_ERROR = 'No se pudo conectar con el servicio. Comprueba tu conexión y vuelve a intentarlo.';
const BAD_RESPONSE = 'El servidor devolvió una respuesta inesperada.';

/** Every request carries the session cookie; the server decides what it is used for. */
async function call(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(`${apiBaseUrl}${path}`, { credentials: 'include', ...init });
  } catch {
    throw new Error(NETWORK_ERROR);
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new Error(BAD_RESPONSE);
  }
}

/** A failed request's error, with the raw code and any per-field issues for forms to place. */
export class ApiRequestError extends Error {
  code: string;
  fields: Record<string, string>;
  constructor(message: string, code: string, fields: Record<string, string> = {}) {
    super(message);
    this.name = 'ApiRequestError';
    this.code = code;
    this.fields = fields;
  }
}

function errorFrom(payload: unknown, messages: Record<string, string>, fallback: string): ApiRequestError {
  const body = payload && typeof payload === 'object' ? (payload as { error?: unknown }).error : null;
  const detail = body && typeof body === 'object' ? (body as { code?: unknown; fields?: unknown }) : null;
  const code = detail && typeof detail.code === 'string' ? detail.code : 'unknown';
  const fields: Record<string, string> = {};
  if (detail && Array.isArray(detail.fields)) {
    for (const issue of detail.fields) {
      if (issue && typeof issue === 'object' && typeof (issue as { field?: unknown }).field === 'string'
          && typeof (issue as { message?: unknown }).message === 'string') {
        fields[(issue as { field: string }).field] = (issue as { message: string }).message;
      }
    }
  }
  return new ApiRequestError(Object.hasOwn(messages, code) ? messages[code] : fallback, code, fields);
}

export function downloadUrl(path: string): string {
  // Accept only the API's versioned download route, never arbitrary external URLs.
  if (!/^\/api\/v1\/cv\/generations\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/pdf$/.test(path)) {
    throw new Error('El servidor devolvió un enlace de descarga inválido.');
  }
  return `${apiBaseUrl}${path}`;
}

export async function generateCv(body: GenerateRequest): Promise<GenerationResponse> {
  const response = await call('/api/v1/cv/generations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await readJson(response);
  if (!payload || typeof payload !== 'object') {
    throw new Error(BAD_RESPONSE);
  }
  const data = payload as Partial<GenerationResponse>;
  if (!response.ok || data.status === 'failed') {
    // Show only our own messages, never provider bodies or server diagnostics.
    const messages: Record<string, string> = {
      not_configured: 'El servicio no está disponible para generar en este momento. Inténtalo más tarde.',
      unauthenticated: 'Tu sesión ha caducado. Inicia sesión de nuevo.',
      provider_error: 'El servicio de generación no pudo completar la solicitud. Vuelve a intentarlo.',
      provider_http_400: 'Gemini rechazó la solicitud (400). Revisa la configuración del modelo y la clave del backend.',
      provider_http_401: 'Gemini rechazó la autenticación (401). Revisa la clave configurada en el backend.',
      provider_http_403: 'Gemini denegó el acceso (403). Revisa los permisos y las restricciones de la clave.',
      provider_http_404: 'Gemini no encontró el recurso solicitado (404). Revisa el modelo configurado en el backend.',
      provider_http_429: 'Gemini ha alcanzado un límite de uso (429). Revisa la cuota de la API antes de reintentar.',
      provider_http_500: 'Gemini tiene un fallo temporal (500). Inténtalo de nuevo más tarde.',
      provider_http_502: 'Gemini no está respondiendo correctamente (502). Inténtalo de nuevo más tarde.',
      provider_http_503: 'Gemini no está disponible temporalmente (503). Inténtalo de nuevo más tarde.',
      provider_http_504: 'Gemini agotó el tiempo de respuesta (504). Inténtalo de nuevo más tarde.',
      provider_network: 'El backend no pudo conectar con Gemini. Revisa su conexión de red o proxy.',
      provider_timeout: 'Gemini tardó demasiado en responder. Inténtalo de nuevo más tarde.',
      provider_tls: 'No se pudo verificar la conexión segura con Gemini. Revisa los certificados del entorno del backend.',
      provider_token_limit: 'La respuesta de Gemini alcanzó el límite de salida y quedó incompleta. Revisa la extensión de los archivos.',
      provider_no_candidate: 'Gemini no devolvió una propuesta de CV. Revisa los archivos antes de reintentar.',
      provider_empty_response: 'Gemini devolvió una respuesta vacía. Vuelve a intentarlo.',
      provider_invalid_response: 'Gemini devolvió una respuesta inesperada. Vuelve a intentarlo.',
      invalid_cv: 'No se pudo obtener un CV válido. Vuelve a intentarlo.',
      compilation_error: 'No se pudo preparar el PDF de una página. Revisa tus archivos y vuelve a intentarlo.',
      invalid_request: 'Revisa los archivos: ambos deben contener texto y no superar los 100.000 caracteres.',
      profile_incomplete: 'Completa tu perfil guardado antes de generar un CV con él.',
    };
    const code = data.error?.code;
    throw new Error(typeof code === 'string' && Object.hasOwn(messages, code)
      ? messages[code] : 'No se pudo generar el CV. Vuelve a intentarlo.');
  }
  if (data.status !== 'completed' || typeof data.id !== 'string' || typeof data.download_url !== 'string') {
    throw new Error('La generación no ha terminado.');
  }
  downloadUrl(data.download_url);
  return { id: data.id, status: data.status, download_url: data.download_url, error: null };
}

// --- Accounts ----------------------------------------------------------------------------

const AUTH_MESSAGES: Record<string, string> = {
  invalid_email: 'Introduce un email válido.',
  weak_password: 'La contraseña debe tener entre 10 y 128 caracteres.',
  email_taken: 'Ya existe una cuenta con este email.',
  invalid_credentials: 'Email o contraseña incorrectos.',
  unauthenticated: 'Inicia sesión para continuar.',
  forbidden_origin: 'Solicitud rechazada. Recarga la página e inténtalo de nuevo.',
  not_configured: 'El servicio no está disponible en este momento.',
  invalid_request: 'Revisa el email y la contraseña.',
};

async function authRequest(path: string, body: { email: string; password: string }): Promise<AuthUser> {
  const response = await call(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const payload = await readJson(response);
  if (!response.ok) throw errorFrom(payload, AUTH_MESSAGES, 'No se pudo completar la solicitud. Vuelve a intentarlo.');
  return payload as AuthUser;
}

export const register = (email: string, password: string) => authRequest('/api/v1/auth/register', { email, password });
export const login = (email: string, password: string) => authRequest('/api/v1/auth/login', { email, password });

export async function logout(): Promise<void> {
  await call('/api/v1/auth/logout', { method: 'POST' });
}

/** null means no session is active; never throws for that case. */
export async function currentUser(): Promise<AuthUser | null> {
  const response = await call('/api/v1/auth/me');
  if (response.status === 401) return null;
  const payload = await readJson(response);
  if (!response.ok) throw errorFrom(payload, AUTH_MESSAGES, 'No se pudo comprobar la sesión.');
  return payload as AuthUser;
}

// --- Profile -------------------------------------------------------------------------------

const PROFILE_MESSAGES: Record<string, string> = {
  ...AUTH_MESSAGES,
  profile_too_large: 'El perfil es demasiado largo. Acorta alguna descripción.',
  profile_invalid: 'El perfil guardado ya no es válido. Revísalo y guárdalo de nuevo.',
  invalid_request: 'Revisa los campos señalados.',
};

function asProfileResponse(payload: unknown): ProfileResponse {
  const body = payload as Partial<ProfileResponse> | null;
  return {
    profile: { ...emptyProfile, ...(body?.profile ?? {}) },
    updated_at: body?.updated_at ?? null,
    missing: body?.missing ?? [],
    complete: body?.complete ?? false,
  };
}

export async function fetchProfile(): Promise<ProfileResponse> {
  const response = await call('/api/v1/profile');
  const payload = await readJson(response);
  if (!response.ok) throw errorFrom(payload, PROFILE_MESSAGES, 'No se pudo cargar el perfil.');
  return asProfileResponse(payload);
}

export async function saveProfile(profile: CandidateProfile): Promise<ProfileResponse> {
  const response = await call('/api/v1/profile', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile),
  });
  const payload = await readJson(response);
  if (!response.ok) throw errorFrom(payload, PROFILE_MESSAGES, 'No se pudo guardar el perfil.');
  return asProfileResponse(payload);
}

export async function clearProfile(): Promise<void> {
  const response = await call('/api/v1/profile', { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw errorFrom(await readJson(response), PROFILE_MESSAGES, 'No se pudo borrar el perfil.');
  }
}
