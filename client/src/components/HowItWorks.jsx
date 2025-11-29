import { cn } from "@/lib/utils";
import {
  IconClipboard,
  IconBrain,
  IconDatabase,
  IconWorld,
  IconShare,
  IconLock,
} from "@tabler/icons-react";

export default function HowItWorks() {
  const features = [
    {
      title: "Paste the forward",
      description:
        "Copy any suspicious WhatsApp forward and paste it into our checker.",
      icon: <IconClipboard />,
    },
    {
      title: "AI extracts claims",
      description:
        "Our system breaks down the message into individual verifiable claims.",
      icon: <IconBrain />,
    },
    {
      title: "Check against memory",
      description:
        "We search our database of 50,000+ previously debunked myths.",
      icon: <IconDatabase />,
    },
    {
      title: "Verify with sources",
      description: "New claims are checked against official sources like PIB, WHO, and more.",
      icon: <IconWorld />,
    },
    {
      title: "Share the truth",
      description: "Get a shareable rebuttal to forward back to your groups.",
      icon: <IconShare />,
    },
    {
      title: "Privacy First",
      description:
        "We don't store your personal messages. Your privacy is our priority.",
      icon: <IconLock />,
    },
  ];
  return (
    <section id="how-it-works" className="py-16 md:py-24">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <h2 className="font-serif text-3xl md:text-4xl lg:text-5xl text-center mb-16 font-semibold">
          How WhatsAMyth Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 relative z-10 mx-auto">
          {features.map((feature, index) => (
            <Feature key={feature.title} {...feature} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}

const Feature = ({
  title,
  description,
  icon,
  index,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col lg:border-r py-10 relative group/feature border-subtle",
        (index === 0 || index === 3) && "lg:border-l border-subtle",
        index < 3 && "lg:border-b border-subtle"
      )}
    >
      {index < 3 && (
        <div className="opacity-0 group-hover/feature:opacity-100 transition duration-200 absolute inset-0 h-full w-full bg-linear-to-t from-(--bg-secondary) to-transparent pointer-events-none" />
      )}
      {index >= 3 && (
        <div className="opacity-0 group-hover/feature:opacity-100 transition duration-200 absolute inset-0 h-full w-full bg-linear-to-b from-(--bg-secondary) to-transparent pointer-events-none" />
      )}
      <div className="mb-4 relative z-10 px-10 text-secondary">
        {icon}
      </div>
      <div className="text-lg font-bold mb-2 relative z-10 px-10">
        <div className="absolute left-0 inset-y-0 h-6 group-hover/feature:h-8 w-1 rounded-tr-full rounded-br-full bg-(--border-medium) group-hover/feature:bg-(--accent-blue) transition-all duration-200 origin-center" />
        <span className="group-hover/feature:translate-x-2 transition duration-200 inline-block text-primary">
          {title}
        </span>
      </div>
      <p className="text-sm text-secondary max-w-xs relative z-10 px-10">
        {description}
      </p>
    </div>
  );
};
