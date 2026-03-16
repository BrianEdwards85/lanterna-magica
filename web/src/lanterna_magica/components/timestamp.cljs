(ns lanterna-magica.components.timestamp
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.util :as util]
   [reagent.core :as r]))

(defn timestamp
  "Renders a relative timestamp span wrapped in a Blueprint Tooltip
   showing the full datetime on hover. iso-str may be nil (renders nothing).
   Uses r/with-let + setInterval to re-render every 60s so relative labels
   stay current in long-lived sessions."
  [iso-str]
  (r/with-let [tick     (r/atom 0)
               interval (js/setInterval #(swap! tick inc) 60000)]
    (when iso-str
      (let [_ @tick]
        [bp/tooltip {:content (util/format-full-datetime iso-str)}
         [:span.text-xs.text-tn-fg-dim
          (util/format-relative-time iso-str)]]))
    (finally (js/clearInterval interval))))
