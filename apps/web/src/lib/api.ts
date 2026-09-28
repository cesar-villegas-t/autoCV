export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export type GenerationStatus = 'pending' | 'generating' | 'completed' | 'failed';
export interface GenerateRequest {
  profile_text: string;
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

export function downloadUrl(path: string): string {
  // Accept only the API's versioned download route, never arbitrary external URLs.
  if (!/^\/api\/v1\/cv\/generations\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/pdf$/.test(path)) {
    throw new Error('El servidor devolvió un enlace de descarga inválido.');
  }
  return `${apiBaseUrl}${path}`;
}

export async function generateCv(body: GenerateRequest): Promise<GenerationResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/api/v1/cv/generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('No se pudo conectar con el servicio. Comprueba tu conexión y vuelve a intentarlo.');
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('El servidor devolvió una respuesta inesperada.');
  }
  if (!payload || typeof payload !== 'object') {
    throw new Error('El servidor devolvió una respuesta inesperada.');
  }
  const data = payload as Partial<GenerationResponse>;
  if (!response.ok || data.status === 'failed') {
    // Show only our own messages, never provider bodies or server diagnostics.
    const messages: Record<string, string> = {
      not_configured: 'El servicio no está disponible para generar en este momento. Inténtalo más tarde.',
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
