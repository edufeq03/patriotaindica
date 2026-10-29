import { NextResponse } from 'next/server';
import { SignJWT, jwtVerify } from 'jose';

export const JWT_SECRET =
  process.env.JWT_SECRET_KEY ||
  'f78a2e19d6c4b50381e9f2a47d0c653891ba42e5d7c0836192fab4e1d3c50782';

export const secretKey = new TextEncoder().encode(JWT_SECRET);

export interface AuthUserPayload {
  id: string;
  name: string;
  email: string;
  role: string;
}

export async function createLocalSessionTokens(user: AuthUserPayload) {
  const accessToken = await new SignJWT({
    sub: user.id,
    name: user.name,
    email: user.email,
    role: user.role,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setIssuer('patriotaindica.com.br')
    .setAudience('patriotaindica-users')
    .setExpirationTime('2h')
    .sign(secretKey);

  const refreshToken = await new SignJWT({
    sub: user.id,
    role: user.role,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setIssuer('patriotaindica.com.br')
    .setAudience('patriotaindica-users')
    .setExpirationTime('7d')
    .sign(secretKey);

  return { accessToken, refreshToken };
}

export async function verifyTokenLocally(token: string): Promise<AuthUserPayload | null> {
  try {
    const { payload } = await jwtVerify(token, secretKey, {
      issuer: 'patriotaindica.com.br',
      audience: 'patriotaindica-users',
    });
    return {
      id: (payload.sub as string) || 'local-user',
      name: (payload.name as string) || 'Usuário Patriota',
      email: (payload.email as string) || 'usuario@patriotaindica.com.br',
      role: (payload.role as string) || 'user',
    };
  } catch {
    return null;
  }
}

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
  refreshToken?: string,
  role?: string
) {
  const isProd = process.env.NODE_ENV === 'production';

  // Access Token: vida curta (15 minutos a 2 horas no fallback)
  response.cookies.set('access_token', accessToken, {
    httpOnly: true,
    secure: isProd,
    sameSite: 'strict',
    path: '/',
    maxAge: 2 * 60 * 60,
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

  if (role === 'admin') {
    response.cookies.set('admin_session', accessToken, {
      httpOnly: true,
      secure: isProd,
      sameSite: 'strict',
      path: '/',
      maxAge: 2 * 60 * 60,
    });
  } else if (role === 'owner') {
    response.cookies.set('owner_session', accessToken, {
      httpOnly: true,
      secure: isProd,
      sameSite: 'strict',
      path: '/',
      maxAge: 2 * 60 * 60,
    });
  }

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

