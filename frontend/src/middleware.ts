import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

const JWT_SECRET = process.env.JWT_SECRET_KEY || '';

const secretKey = new TextEncoder().encode(JWT_SECRET || 'dev_insecure_key_for_build_only_32_chars_min');

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const requestHeaders = new Headers(request.headers);

  // Injeção transparente de Bearer token para chamadas ao backend /api/v1 a partir do cookie HttpOnly
  const accessToken =
    request.cookies.get('access_token')?.value ||
    request.cookies.get('admin_session')?.value ||
    request.cookies.get('owner_session')?.value;

  if (
    accessToken &&
    (!requestHeaders.has('authorization') ||
      requestHeaders.get('authorization') === 'Bearer cookie_session')
  ) {
    requestHeaders.set('authorization', `Bearer ${accessToken}`);
  }

  // 1. Verificação e Proteção de Rotas Restritas (/admin e /painel-empresa)
  const isPainelEmpresa = pathname.startsWith('/painel-empresa');
  const isAdmin = pathname.startsWith('/admin');

  if (isPainelEmpresa || isAdmin) {
    let isAuthenticated = false;
    let userRole = '';

    if (accessToken) {
      try {
        const { payload } = await jwtVerify(accessToken, secretKey, {
          issuer: 'patriotaindica.com.br',
          audience: 'patriotaindica-users',
        });
        isAuthenticated = true;
        userRole = (payload.role as string) || '';
      } catch {
        isAuthenticated = false;
      }
    }

    // Se for subrota de /admin que não seja a página raiz de login, redireciona para /admin
    if (isAdmin && pathname !== '/admin') {
      if (!isAuthenticated || userRole !== 'admin') {
        const loginUrl = request.nextUrl.clone();
        loginUrl.pathname = '/admin';
        loginUrl.searchParams.set('auth_required', '1');
        return NextResponse.redirect(loginUrl);
      }
    }
  }

  // 2. Content Security Policy (CSP) e Cabeçalhos de Segurança da Borda (T2.2)
  const cspHeader = `
    default-src 'self';
    script-src 'self' 'unsafe-inline' 'unsafe-eval' https://sdk.mercadopago.com;
    style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
    font-src 'self' https://fonts.gstatic.com data:;
    img-src 'self' data: blob: https: http:;
    connect-src 'self' https: http: ws: wss:;
    frame-src 'self' https://sdk.mercadopago.com;
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
  `
    .replace(/\s{2,}/g, ' ')
    .trim();

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Aplica CSP e headers defensivos padrão OWASP
  response.headers.set('Content-Security-Policy', cspHeader);
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(self)'
  );
  response.headers.set('x-patriota-security', 'enforced');

  return response;
}

export const config = {
  matcher: [
    /*
     * Aplica em todas as rotas exceto arquivos estáticos, favicon, imagens
     */
    '/((?!_next/static|_next/image|favicon.ico|icon.png|icon.svg|static/).*)',
  ],
};
