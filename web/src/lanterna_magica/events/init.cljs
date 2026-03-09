(ns lanterna-magica.events.init
  (:require
   [lanterna-magica.config :as config]
   [lanterna-magica.db :as db]
   [lanterna-magica.events :as-alias events]
   [lanterna-magica.routes :as routes]
   [re-frame.core :as rf]
   [re-graph.core :as re-graph]))

(rf/reg-event-fx
  ::events/initialize-db
  (fn [_ _]
    {:db db/default-db}))

(rf/reg-fx
  :navigate
  (fn [route-name]
    (routes/navigate! route-name)))

(rf/reg-event-fx
  ::events/boot
  (fn [_ _]
    {:dispatch-n [[::re-graph/init {:ws   nil
                                    :http {:url config/GRAPHQL_URL}}]
                  [::events/fetch-dimension-types]]}))
