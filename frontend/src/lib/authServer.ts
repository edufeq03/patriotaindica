import { NextResponse } from 'next/server';

export function getBackendUrl(): string {
  // Em produção/Docker, INTERNAL_API_URL aponta para http://backend:8000/api/v1
  // No desenvolvimento local, fallback para localhost
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000/api/v1'
  );
}

export function setAuthCookies(
  response: NextResponse,
  accessToken: string,
  refreshToken?: string
) {
  const isProd = process.env.NODE_ENV === 'production';

  // Access Token: vida curta (15 minutos)
  response.cookies.set('access_token', accessToken, {
    httpOnly: true,
    secure: isProd,
    sameSite: 'strict',
    path: '/',
    maxAge: 15 * 60,
  });

  // Refresh Token: rotativo (7 dias)
  if (refreshToken) {
    response.cookies.set('refresh_token', refreshToken, {
      httpOnly: true,
      secure: isProd,
      sameSite: 'strict',
      path: '/',
      maxAge: 7 * 24 * 60 * 60,
    });
  }

  // Cookie não-sensível para o frontend saber o papel do usuário logado (sem expor token)
  return response;
}

export function clearAuthCookies(response: NextResponse) {
  const isProd = process.env.NODE_ENV === 'production';
  response.cookies.set('access_token', '', {
    httpOnly: true,
    secure: isProd,
    sameSite: 'strict',
    path: '/',
    maxAge: 0,
  });
  response.cookies.set('refresh_token', '', {
    httpOnly: true,
    secure: isProd,
    sameSite: 'strict',
    path: '/',
    maxAge: 0,
  });
  response.cookies.set('admin_session', '', {
    path: '/',
    maxAge: 0,
  });
  response.cookies.set('owner_session', '', {
    path: '/',
    maxAge: 0,
  });
  return response;
}
