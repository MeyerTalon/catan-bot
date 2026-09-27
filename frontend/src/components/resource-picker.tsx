import React from "react";
import { Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  handTotal,
  RESOURCE_COLOR,
  RESOURCE_LABEL,
  RESOURCES,
  type Hand,
  type Resource,
} from "@/lib/game";

export const ResourceDot: React.FC<{ resource: Resource }> = ({ resource }) => (
  <span
    className="inline-block size-3 shrink-0 rounded-sm"
    style={{ backgroundColor: RESOURCE_COLOR[resource] }}
  />
);

type ResourcePickerProps = {
  value: Hand;
  onChange: (value: Hand) => void;
  /** Per-resource ceiling, e.g. the cards in hand. */
  max?: Hand;
  /** Ceiling on the total across resources. */
  totalMax?: number;
};

/** A -/+ counter per resource for building discards and trade offers. */
export const ResourcePicker: React.FC<ResourcePickerProps> = ({
  value,
  onChange,
  max,
  totalMax,
}) => {
  const total = handTotal(value);
  const set = (r: Resource, n: number) => onChange({ ...value, [r]: n });

  return (
    <div className="flex flex-col gap-1">
      {RESOURCES.map((r) => {
        const n = value[r] ?? 0;
        const limit = max ? (max[r] ?? 0) : Infinity;
        const canAdd =
          n < limit && (totalMax === undefined || total < totalMax);
        return (
          <div key={r} className="flex items-center gap-2 text-sm">
            <ResourceDot resource={r} />
            <span className="w-14">{RESOURCE_LABEL[r]}</span>
            <Button
              size="icon-xs"
              variant="outline"
              aria-label={`Fewer ${r}`}
              disabled={n === 0}
              onClick={() => set(r, n - 1)}
            >
              <Minus />
            </Button>
            <span className="w-5 text-center tabular-nums">{n}</span>
            <Button
              size="icon-xs"
              variant="outline"
              aria-label={`More ${r}`}
              disabled={!canAdd}
              onClick={() => set(r, n + 1)}
            >
              <Plus />
            </Button>
            {max && (
              <span className="text-xs text-muted-foreground">
                of {max[r] ?? 0}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};

type ResourceChoiceProps = {
  options: Resource[];
  value: Resource | null;
  onChange: (value: Resource) => void;
  /** Extra text after each label, e.g. a trade rate. */
  suffix?: (resource: Resource) => string;
};

/** A row of toggle buttons for choosing one resource. */
export const ResourceChoice: React.FC<ResourceChoiceProps> = ({
  options,
  value,
  onChange,
  suffix,
}) => (
  <div className="flex flex-wrap gap-1">
    {options.map((r) => (
      <Button
        key={r}
        size="xs"
        variant={value === r ? "default" : "outline"}
        onClick={() => onChange(r)}
      >
        <ResourceDot resource={r} />
        {RESOURCE_LABEL[r]}
        {suffix?.(r)}
      </Button>
    ))}
  </div>
);
