(ns lanterna-magica.components.toaster
  (:require
   ["@blueprintjs/core" :as bp]))

(defonce ^:private instance (atom nil))

(defn init! []
  (.then (bp/OverlayToaster.create #js {:position "top-right"})
         #(reset! instance %)))

(defn show! [{:keys [message intent timeout]
              :or   {intent "success" timeout 3000}}]
  (when-let [t @instance]
    (.show t #js {:message message :intent intent :timeout timeout})))
