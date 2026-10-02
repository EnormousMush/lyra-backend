import { Link } from "react-router-dom";
import { Wordmark } from "../components/Shell";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[1100px] flex-col px-5 py-6 md:px-8">
      <Link to="/">
        <Wordmark />
      </Link>
      <div className="flex flex-1 flex-col justify-center">
        <h1 className="display text-6xl">This page is silent.</h1>
        <p className="mt-4 text-slate">The address does not match anything in Lyra.</p>
        <Link to="/library" className="btn btn-primary mt-8 self-start">
          Go to library
        </Link>
      </div>
    </main>
  );
}
