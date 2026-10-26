import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Proteção server-side de rotas administrativas e restritas
  if (pathname.startsWith('/painel-empresa')) {
    const sessionCookie = request.cookies.get('owner_session')?.value || request.cookies.get('admin_session')?.value;
    const authHeader = request.headers.get('authorization');

    if (!sessionCookie && !authHeader) {
      // Redireciona para home ou login se não autenticado
      const url = request.nextUrl.clone();
      url.pathname = '/';
      url.searchParams.set('auth_required', '1');
      return NextResponse.redirect(url);
    }
  }

  // Adiciona header para rastreamento de requisição limpa
  const response = NextResponse.next();
  response.headers.set('x-patriota-security', 'enforced');
  return response;
}

export const config = {
  matcher: ['/painel-empresa/:path*'],
};
