import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = {title:'OpenResearch Agent',description:'Trace every finding to its evidence.'};
export default function Layout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>}
